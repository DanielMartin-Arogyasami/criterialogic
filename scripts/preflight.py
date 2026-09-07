#!/usr/bin/env python3
"""Preflight — can this installation actually run? One command, no API key, no network.

    python scripts/preflight.py

Checks the environment, resolves the committed data, loads it, then runs a small real
evaluation through both arms and asserts the diagnostics behave as designed. Each check
prints PASS or FAIL with the reason and what to do about it; the exit code is the number
of failures, so it is usable in CI.

This exists because the failure modes of a fresh checkout are boring and specific — wrong
Python, missing pydantic, a working directory the data cannot be found from, an atom pool
that was never built — and each of them otherwise surfaces as a traceback several layers
into the call stack.
"""
from __future__ import annotations

import platform
import sys
import traceback

MIN_PYTHON = (3, 10)
_results: list[tuple[bool, str, str]] = []


def check(name: str):
    """Decorator: run a check, record PASS/FAIL, never let one failure stop the rest."""
    def wrap(fn):
        try:
            detail = fn() or ""
            _results.append((True, name, str(detail)))
        except Exception as e:
            hint = getattr(e, "preflight_hint", "")
            detail = f"{type(e).__name__}: {e}"
            if hint:
                detail += f"\n         -> {hint}"
            _results.append((False, name, detail))
        return fn
    return wrap


def fail(message: str, hint: str = "") -> None:
    err = RuntimeError(message)
    err.preflight_hint = hint  # type: ignore[attr-defined]
    raise err


# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #
@check("Python version")
def _python():
    if sys.version_info < MIN_PYTHON:
        fail(f"Python {platform.python_version()} is below the required "
             f"{'.'.join(map(str, MIN_PYTHON))}.",
             "The schema uses pydantic v2 with PEP 604 unions.")
    return platform.python_version()


@check("pydantic v2 importable")
def _pydantic():
    try:
        import pydantic
    except ImportError:
        fail("pydantic is not installed.",
             "pip install -e .   (corporate networks: point pip at your organisation's "
             "package index rather than PyPI)")
    major = int(pydantic.VERSION.split(".")[0])
    if major < 2:
        fail(f"pydantic {pydantic.VERSION} is v1; the schema requires v2.",
             "pip install 'pydantic>=2,<3'")
    return f"pydantic {pydantic.VERSION}"


@check("package importable")
def _package():
    import criterialogic
    return f"criterialogic {criterialogic.__version__}, schema {criterialogic.SCHEMA_VERSION}"


@check("statistics layer has no third-party dependency")
def _stats_pure():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "cl_stats_pure", Path(__file__).resolve().parents[1] / "criterialogic/metrics/stats.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # would fail if it had grown an import
    lo, hi = mod.wilson_interval(36, 60)
    if not (abs(lo - 0.4737) < 1e-3 and abs(hi - 0.7143) < 1e-3):
        fail(f"wilson_interval(36, 60) returned ({lo}, {hi}); expected (0.4737, 0.7143).")
    return "loads standalone; wilson_interval spot-check matches"


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@check("data directory resolved")
def _data_dir():
    from criterialogic.data.paths import describe_resolution
    info = describe_resolution()
    if not info["resolved"]:
        fail(f"No data directory found. Searched: {info['candidates']}",
             "Run from a clone, or set CRITERIALOGIC_DATA_DIR to the directory holding "
             "ctgov_cache/ and ctgov_atom_pool.json.")
    return info["resolved"]


@check("ClinicalTrials.gov snapshot present")
def _snapshot():
    from criterialogic.data.loaders.ctgov import load_cached_studies, read_manifest
    studies = load_cached_studies()
    if not studies:
        fail("No cached studies found.",
             "python scripts/fetch_ctgov_snapshot.py --limit 300 --first-posted-from 2026-01-01")
    manifest = read_manifest() or {}
    return (f"{len(studies)} studies, snapshot "
            f"{manifest.get('snapshot_id', 'unknown')}, frame "
            f"{manifest.get('advanced_expression', 'unrecorded')!r}")


@check("atom pool loadable")
def _pool():
    from criterialogic.data.atom_pool import load_ctgov_pool
    pool = load_ctgov_pool()
    if len(pool) < 20:
        fail(f"Pool has only {len(pool)} atoms; too few to compose from.",
             "Rebuild with scripts/fetch_ctgov_snapshot.py --offline")
    dated = [e.first_posted for e in pool.entries if e.first_posted]
    return (f"{len(pool)} atoms, digest {pool.sha256[:12]}…, "
            f"first-posted {min(dated, default='?')}..{max(dated, default='?')}")


# --------------------------------------------------------------------------- #
# Arm 1
# --------------------------------------------------------------------------- #
@check("Arm 1: criteria segment from the snapshot")
def _arm1_build():
    from criterialogic.data.real_criteria import (
        build_criterion_forms,
        polarity_distribution,
        structure_distribution,
    )
    forms, stats = build_criterion_forms(max_per_study=4)
    if not forms:
        fail("Segmentation produced no criteria.",
             "Inspect the cached eligibility text; an empty result is a real finding, "
             "not something to fix by loosening the extraction rules.")
    pol = polarity_distribution(forms)
    depth = structure_distribution(forms)
    note = ""
    if stats.mapped_coordinated == 0:
        note = ("  NOTE: zero coordinated criteria — Arm 1 is entirely single-predicate. "
                "Say so in the paper rather than describing coordination as if it fires.")
    if "exclusion" not in pol:
        note += "\n         NOTE: no exclusion criteria, so polarity is untested."
    return (f"{len(forms)} criteria from "
            f"{len({f.metadata['trial_id'] for f in forms})} trials; "
            f"mapping rate {stats.to_json()['mapping_rate']}; polarity {pol}; "
            f"depths {depth}{note}")


@check("Arm 1: evaluation runs and the oracle baseline is exact")
def _arm1_run():
    from criterialogic.data.real_criteria import build_criterion_forms
    from criterialogic.eval.runner import run_task
    from criterialogic.models import RuleBasedModel
    from criterialogic.tasks.real_criteria import generate_real_criteria_items
    forms, _ = build_criterion_forms(max_per_study=2, limit=25)
    items = generate_real_criteria_items(forms, n_per_criterion=2, seed=17)
    res = run_task(RuleBasedModel(), items, seed=17)
    f1 = res["metrics"]["overall_micro_f1"]
    if f1 != 1.0:
        fail(f"rule_based scored micro-F1 {f1} on structured input, expected exactly 1.0.",
             "rule_based evaluates the same expression the oracle labelled, so anything "
             "below 1.0 means the model and the oracle have diverged — a real bug.")
    return f"{len(items)} items, micro-F1 {f1} (oracle baseline, perfect by construction)"


# --------------------------------------------------------------------------- #
# Arm 2
# --------------------------------------------------------------------------- #
@check("Arm 2: generator is deterministic")
def _arm2_determinism():
    from criterialogic.tasks.compositional import generate_compositional_items
    a = generate_compositional_items(n_per_depth=6, max_depth=3, seed=29)
    b = generate_compositional_items(n_per_depth=6, max_depth=3, seed=29)
    if [i.gold for i in a] != [i.gold for i in b]:
        fail("Two runs with the same seed produced different gold labels.")
    if [i.criterion.model_dump_json() for i in a] != [i.criterion.model_dump_json() for i in b]:
        fail("Two runs with the same seed produced different criteria.")
    return f"{len(a)} items reproduce byte-identically"


@check("Arm 2: depth is controllable and stratified")
def _arm2_depths():
    from criterialogic.eval.runner import run_task
    from criterialogic.models import NegationBlindModel
    from criterialogic.tasks.compositional import generate_compositional_items
    items = generate_compositional_items(n_per_depth=8, seed=29, depths=[2, 5])
    got = {i.depth for i in items}
    if got != {2, 5}:
        fail(f"Requested depths [2, 5] but generated {sorted(got)}.")
    res = run_task(NegationBlindModel(), items, seed=29)
    if "trend" not in res["metrics"]:
        fail("Two depth levels produced no trend statistics.")
    return (f"depths {sorted(got)}; rho "
            f"{res['metrics']['trend']['spearman']['rho']}, "
            f"mode {res['metrics']['trend']['spearman']['mode']}")


@check("diagnostics behave as designed")
def _diagnostics():
    from criterialogic.eval.runner import run_task
    from criterialogic.models import NegationBlindModel
    from criterialogic.tasks.compositional import generate_compositional_items
    items = generate_compositional_items(n_per_depth=10, max_depth=3, seed=29)
    res = run_task(NegationBlindModel(), items, seed=29)
    tax = res["failure_taxonomy"]
    if tax["n_errors"] == 0:
        fail("The deliberately-broken baseline made no errors; the harness is not wired.")
    if res["calibration"]["usable_confidence_signal"] is not False:
        fail("A constant-confidence model was reported as having a usable confidence "
             "signal; the degenerate-confidence gate is not firing.")
    if not res["per_item_predictions"]:
        fail("per_item_predictions is empty; aggregates could not be recomputed later.")
    return (f"{tax['n_errors']} errors -> {tax['categories']}; "
            f"labeller v{tax['labeller_version']}; "
            f"{len(res['per_item_predictions'])} per-item rows persisted")


@check("leaderboard round-trip")
def _leaderboard():
    import json
    import tempfile
    from pathlib import Path

    from criterialogic.leaderboard.score import score_submission
    from criterialogic.leaderboard.submit import load_submission, validate_against_items
    from criterialogic.models import RuleBasedModel
    from criterialogic.tasks.compositional import generate_compositional_items
    items = generate_compositional_items(n_per_depth=5, max_depth=2, seed=1)
    preds = RuleBasedModel().predict_batch(items)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "sub.json"
        p.write_text(json.dumps({"model": "rule_based", "task": "compositional",
                                 "predictions": [x.model_dump() for x in preds]}))
        sub = load_submission(str(p))
        validate_against_items(sub, items)
        scored = score_submission(sub, items)
    return f"scored {scored['n_items']} items, accuracy {scored['metrics']['overall_accuracy']}"


@check("annotation export is blind and formula-safe")
def _annotation():
    import csv
    import tempfile

    from criterialogic.models import NegationBlindModel
    from criterialogic.tasks.compositional import generate_compositional_items
    from criterialogic.taxonomy.reliability import export_for_annotation, sample_error_set
    items = generate_compositional_items(n_per_depth=10, max_depth=3, seed=29)
    runs = {"compositional::negation_blind": (items, NegationBlindModel().predict_batch(items))}
    sample = sample_error_set(runs, n=10, seed=5)
    if not sample:
        fail("No errors available to sample for annotation.")
    with tempfile.TemporaryDirectory() as d:
        info = export_for_annotation(sample, d)
        for path in info["annotator_files"]:
            header = next(csv.reader(open(path, encoding="utf-8")))
            if "automatic_category" in header:
                fail("The annotator file exposes the heuristic label; the pass is not blind.")
            for row in csv.DictReader(open(path, encoding="utf-8")):
                for cell in row.values():
                    if cell and cell[0] in "=+-@":
                        fail(f"Unescaped formula-leading cell in {path}: {cell[:40]!r}")
    return f"{info['n_items']} items, 2 blind files, automatic labels held back"


def main() -> int:
    print("CriteriaLogic preflight\n" + "=" * 72)
    width = max(len(n) for _, n, _ in _results)
    failures = 0
    for ok, name, detail in _results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  [{mark}] {name.ljust(width)}  {detail}")
    print("=" * 72)
    if failures:
        print(f"{failures} check(s) failed. Nothing above needs a network connection or an "
              f"API key, so each one is a local problem with a local fix.")
    else:
        print("All checks passed. Both arms run end to end offline.")
        print("Real model results need an API key — see RUN.md section 3.")
    return failures


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # pragma: no cover
        traceback.print_exc()
        sys.exit(99)
