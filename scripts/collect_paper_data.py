#!/usr/bin/env python3
"""Collect every number the manuscript needs, and check the manuscript against them.

    python scripts/collect_paper_data.py                 # collect -> results/paper_data.md
    python scripts/collect_paper_data.py --verify         # diff the numbers extract against the artifacts
    python scripts/collect_paper_data.py --run            # also run the offline arms first

Two outputs:

``results/paper_data.json``
    Machine-readable. Every figure, with the provenance and the integrity gates attached.

``results/paper_data.md``
    Paste-ready. The tables are formatted to match the manuscript's own section headings,
    so filling Section 3 and Section 7 is a copy rather than a transcription — which is the
    step where numbers get mistyped.

Design rules, both learned from the v0.1 audit
----------------------------------------------
**Recompute, never carry forward.** Every aggregate is derived here from the persisted
per-item predictions, not copied from a stored aggregate. The v0.1 run stored only
aggregates, so when the audit found the selective-accuracy curves were artefacts of list
order it could detect the problem algebraically but not correct it.

**The integrity gates live in the collector, not beside it.** v0.1 kept the discrepancy
list as prose maintained alongside the JSON, and it drifted — the machine-readable list was
two entries behind the human one. Here the gates run as part of collection and their
verdicts go into both outputs, so a blocking finding cannot be absent from the numbers a
reader is handed.

**A bracket is a real answer.** Where an experiment has not been run this prints the
bracket the manuscript should keep, and says which command fills it. It never estimates.

The main path is standard-library only — ``stats.py`` is loaded by file path — so this runs
on a checkout with nothing installed. Two enrichments need pydantic because they regenerate
items: the exposure stratification (§7.3) and the Arm 1 composition (§3.2). Both are
skipped with a note rather than failing the run.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_stats():
    """Load the statistics layer without importing the package (which needs pydantic)."""
    spec = importlib.util.spec_from_file_location(
        "cl_stats", ROOT / "criterialogic/metrics/stats.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load_stats()

#: Per-depth files from the v0.2 gpt-5-nano / prompt-v1 sweep. Used only as a labelled
#: fallback, and never mixed into a table whose current run is a different model or prompt.
REPORTED_SWEEP = {f"compositional_d{d}::openai": {"depth": d, "n_per_depth": 60,
                                                  "seed": 101 + d} for d in range(2, 7)}
REPORTED_MIXED = "compositional_large::openai"
CURRENT_SWEEP_LABEL = "compositional::openai"
CURRENT_SWEEP_MODEL = "gpt-4o-mini"
CURRENT_SWEEP_PROMPT = "2"


def _repo_rel(path: Path) -> str:
    """Path relative to the repo root, so committed artifacts carry no machine path."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _identity(run: dict) -> dict:
    """Model, prompt version, and whether this run came from the legacy bundle."""
    model_block = run.get("model") if isinstance(run.get("model"), dict) else {}
    inf = run.get("inference") if isinstance(run.get("inference"), dict) else {}
    if inf and "requested_temperature" not in inf and "model" not in inf:
        inf = {}
    model = model_block.get("model") or inf.get("model")
    prompt = model_block.get("prompt_version")
    if prompt is None:
        prompt = inf.get("prompt_version")
    src = str(run.get("source") or "")
    legacy = "missing_runs" in src.replace("\\", "/")
    if legacy and not model:
        model = "gpt-5-nano"
    if legacy and prompt is None:
        prompt = "1"
    return {
        "model": str(model) if model else None,
        "prompt_version": str(prompt) if prompt is not None else None,
        "legacy": legacy,
        "source": src,
    }


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_runs(results_dir: Path) -> dict:
    """Every run with persisted per-item predictions, keyed by label."""
    runs: dict = {}
    results_dir = Path(results_dir).resolve()
    legacy = results_dir / "missing" / "missing_runs.json"
    if legacy.is_file():
        payload = json.loads(legacy.read_text(encoding="utf-8"))
        for label, run in payload.get("runs", {}).items():
            if run.get("per_item_predictions"):
                src = _repo_rel(legacy)
                runs[label] = {"source": src,
                               "inference": payload.get("inference_parameters", {}),
                               **run}
    for path in sorted(results_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get("per_item_predictions") or "task" not in data:
            continue
        label = f"{data['task']}::{data.get('model', {}).get('name', path.stem)}"
        src = _repo_rel(path)
        runs[label] = {"source": src, **data}
    return runs


def _rows(run: dict) -> list[tuple[float, bool]]:
    return [(p["confidence"], p["correct"]) for p in run["per_item_predictions"]]


def _counts(run: dict) -> tuple[int, int]:
    pips = run["per_item_predictions"]
    return sum(1 for p in pips if p["correct"]), len(pips)


def summarise_run(label: str, run: dict) -> dict:
    """Recompute every headline figure for one run from its per-item predictions."""
    rows = _rows(run)
    k, n = _counts(run)
    pips = run["per_item_predictions"]
    errors = [p for p in pips if not p["correct"]]
    rationales = [(p.get("rationale") or "").strip() for p in pips if p.get("rationale")]
    err_rationales = [(p.get("rationale") or "").strip() for p in errors if p.get("rationale")]
    if not err_rationales:  # legacy runs carry rationales on the error subset only
        err_rationales = [(e.get("rationale") or "").strip()
                          for e in run.get("error_items", []) if e.get("rationale")]
    raw_ece = S.expected_calibration_error(rows)
    raw_conf = (sum(c for c, _ in rows) / n) if n else None
    raw_acc = (k / n) if n else None
    ident = _identity(run)
    return {
        "label": label,
        "source": run.get("source"),
        "n_items": n,
        "n_correct": k,
        "accuracy": round(raw_acc, 4) if n else None,
        "wilson_95": [round(v, 4) for v in S.wilson_interval(k, n)],
        "n_errors": n - k,
        "ece": round(raw_ece, 4),
        "mean_confidence": round(raw_conf, 4) if n else None,
        # Display values, rounded ONCE from the raw figure. Rounding to 4 and then
        # formatting to 3 sends a value ending .xxx5 the other way — d3's ECE renders as
        # 0.171 that way and 0.170 this way, and two artifacts disagreeing by a display
        # convention is exactly how a paper drifts from its data.
        "accuracy_3dp": round(raw_acc, 3) if n else None,
        "ece_3dp": round(raw_ece, 3),
        "mean_confidence_3dp": round(raw_conf, 3) if n else None,
        "n_abstain": sum(1 for p in pips if p.get("abstain")),
        "usable_confidence_signal": not S.is_degenerate_confidence(rows),
        "selective_accuracy": S.selective_accuracy(rows),
        "distinct_error_rationales": len(set(err_rationales)) if err_rationales else None,
        "n_errors_with_rationale": len(err_rationales),
        "n_unanswerable_errors": sum(1 for p in errors if p.get("unanswerable")) or None,
        "by_depth": _by_depth(pips),
        "_has_rationales": bool(rationales),
        "legacy": ident["legacy"],
        "eval_model": ident["model"],
        "prompt_version": ident["prompt_version"],
    }


def _by_depth(pips: list[dict]) -> dict:
    out: dict[int, list[int]] = {}
    for p in pips:
        d = p.get("depth")
        if d is None:
            continue
        k, n = out.get(d, (0, 0))
        out[d] = (k + int(p["correct"]), n + 1)
    return {str(d): {"n_correct": v[0], "n": v[1],
                     "accuracy": round(v[0] / v[1], 4),
                     "wilson_95": [round(x, 4) for x in S.wilson_interval(*v)]}
            for d, v in sorted(out.items())}


# --------------------------------------------------------------------------- #
# Section 3 — dataset composition
# --------------------------------------------------------------------------- #
def section3(data_dir: Path) -> dict:
    out: dict = {"snapshot": None, "atom_pool": None, "arm1": None}
    manifest = data_dir / "ctgov_cache" / "MANIFEST.json"
    if manifest.is_file():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        out["snapshot"] = {
            "snapshot_id": m.get("snapshot_id", "unrecorded"),
            "frame": m.get("frame") or m.get("advanced_expression"),
            "advanced_expression": m.get("advanced_expression"),
            "n_studies": m.get("n_studies_cached"),
            "fetched_utc": m.get("fetched_utc"),
            "first_posted_from": m.get("first_posted_from"),
        }
    pool = data_dir / "ctgov_atom_pool.json"
    if pool.is_file():
        p = json.loads(pool.read_text(encoding="utf-8"))
        atoms = p.get("atoms", [])
        ex = p.get("extraction", {})
        dated = [a["first_posted"] for a in atoms if a.get("first_posted")]
        sections: dict[str, int] = {}
        for a in atoms:
            sections[a.get("section", "?")] = sections.get(a.get("section", "?"), 0) + 1
        considered = ex.get("sentences_considered") or 0
        matched = ex.get("sentences_matched") or 0
        out["atom_pool"] = {
            "n_atoms": len(atoms),
            "n_source_trials": len({a.get("nct_id") for a in atoms if a.get("nct_id")}),
            "sentences_considered": considered,
            "sentences_matched": matched,
            "match_rate": round(matched / considered, 4) if considered else None,
            "by_section": sections,
            "first_posted_range": [min(dated, default=None), max(dated, default=None)],
            "sha256": None,  # computed by the loader; not needed for the manuscript
        }
    out["arm1"] = _arm1_composition(data_dir)
    return out


def _arm1_composition(data_dir: Path) -> dict:
    """Arm 1 composition. Needs pydantic, so degrade to a bracket rather than failing."""
    try:
        sys.path.insert(0, str(ROOT))
        from criterialogic.data.real_criteria import (
            build_criterion_forms,
            polarity_distribution,
            structure_distribution,
        )
    except Exception as e:
        return {"status": "requires pydantic",
                "detail": f"{type(e).__name__}: {e}",
                "fill_with": "python scripts/build_real_criteria.py --stats"}
    forms, stats = build_criterion_forms(cache_dir=data_dir / "ctgov_cache", max_per_study=4)
    js = stats.to_json()
    return {
        "status": "computed",
        "n_criteria": len(forms),
        "n_trials": len({f.metadata.get("trial_id") for f in forms}),
        "segmentation": js,
        "polarity": polarity_distribution(forms),
        "depth_histogram": structure_distribution(forms),
        "coordinated_criteria": js.get("criteria_mapped_coordinated"),
    }


# --------------------------------------------------------------------------- #
# Section 7 — depth sweep, mixed set, exposure, taxonomy, calibration
# --------------------------------------------------------------------------- #
def _sweep_from_rows(rows: list[dict]) -> dict:
    per_depth = {r["depth"]: (r["n"] - r["n_errors"], r["n"]) for r in rows}
    trend = S.depth_trend(per_depth)
    pooled_k = sum(v[0] for v in per_depth.values())
    pooled_n = sum(v[1] for v in per_depth.values())
    return {
        "status": "computed",
        "rows": rows,
        "pooled": {"n_correct": pooled_k, "n": pooled_n,
                   "accuracy": round(pooled_k / pooled_n, 4),
                   "wilson_95": [round(v, 4) for v in S.wilson_interval(pooled_k, pooled_n)]},
        "trend": trend,
        "ci_separated_pairs": [p["depths"] for p in trend["pairwise"] if not p["cis_overlap"]],
        "unresolved_pairs": [{"depths": p["depths"], "n_per_depth_needed": p["n_per_depth_needed"]}
                             for p in trend["pairwise"] if p["cis_overlap"]],
    }


def _row_from_summary(depth: int, seed, s: dict) -> dict:
    return {
        "depth": depth, "seed": seed,
        "accuracy": s["accuracy"],
        "accuracy_3dp": s["accuracy_3dp"],
        "wilson_95": s["wilson_95"],
        "n": s["n_items"],
        "n_errors": s["n_errors"],
        "ece": s["ece"],
        "ece_3dp": s["ece_3dp"],
        "mean_confidence": s["mean_confidence"],
        "mean_confidence_3dp": s["mean_confidence_3dp"],
    }


def _not_run_sweep(gates: list[dict] | None = None) -> dict:
    return {"status": "not run",
            "fill_with": ("python scripts/run_eval.py --task compositional "
                          "--depths 2,3,4,5,6 --n-per-depth 60 --model openai"),
            "_gates": gates or []}


_DIAGNOSTIC_NAMES = {"rule_based", "negation_blind"}


def _current_combined(summaries: dict, runs: dict | None) -> str | None:
    """The current LLM sweep, never a diagnostic and never a legacy per-depth file."""
    if not runs:
        return None
    if CURRENT_SWEEP_LABEL in summaries:
        return CURRENT_SWEEP_LABEL
    candidates: list[str] = []
    for lbl in summaries:
        if not lbl.startswith("compositional::"):
            continue
        ident = _identity(runs[lbl])
        if ident["legacy"]:
            continue
        name = None
        model = runs[lbl].get("model")
        if isinstance(model, dict):
            name = model.get("name")
        if name in _DIAGNOSTIC_NAMES:
            continue
        candidates.append(lbl)
    return candidates[0] if candidates else None


def depth_sweep(summaries: dict, runs: dict | None = None) -> dict:
    # Prefer a combined compositional::<model> run (the official T2 command, prompt v2).
    # Legacy per-depth files are refused when they name a different model or prompt.
    label = _current_combined(summaries, runs)
    if label and runs:
        ident = _identity(runs[label])
        pips = runs[label]["per_item_predictions"]
        seed = (runs[label].get("repro") or {}).get("seed")
        depths = sorted({p["depth"] for p in pips if p.get("depth") is not None})
        if len(depths) >= 2:
            rows = []
            for d in depths:
                slice_pips = [p for p in pips if p.get("depth") == d]
                s = summarise_run(f"{label}@d{d}", {"per_item_predictions": slice_pips,
                                                    "source": runs[label].get("source"),
                                                    "model": runs[label].get("model")})
                row = _row_from_summary(d, seed, s)
                row["model"] = ident["model"]
                row["prompt_version"] = ident["prompt_version"]
                row["legacy"] = False
                rows.append(row)
            out = _sweep_from_rows(rows)
            out["source_label"] = label
            out["model"] = ident["model"]
            out["prompt_version"] = ident["prompt_version"]
            out["legacy"] = False
            out["_gates"] = []
            return out

    present = {lbl: spec for lbl, spec in REPORTED_SWEEP.items() if lbl in summaries}
    if len(present) >= 2 and runs:
        ids = {lbl: _identity(runs[lbl]) for lbl in present}
        current_id = (_identity(runs[label]) if label else {
            "model": CURRENT_SWEEP_MODEL, "prompt_version": CURRENT_SWEEP_PROMPT,
            "source": f"results/{CURRENT_SWEEP_LABEL.replace('::', '__')}.json",
        })
        mismatched = [
            lbl for lbl, ident in ids.items()
            if (ident["model"], ident["prompt_version"])
            != (current_id["model"], current_id["prompt_version"])
        ]
        if mismatched or any(ident["legacy"] for ident in ids.values()):
            sample = ids[mismatched[0] if mismatched else next(iter(ids))]
            return _not_run_sweep([{
                "level": "BLOCK",
                "subject": "depth sweep source",
                "finding": (
                    f"Refused to build the depth sweep from {sorted(present)} "
                    f"({sample['model']}, prompt {sample['prompt_version']}, "
                    f"source {sample['source']}) because those runs do not match the "
                    f"current run ({current_id['model']}, prompt "
                    f"{current_id['prompt_version']}, source {current_id['source']})."
                ),
                "action": ("Use the current compositional:: run. Do not report the "
                           "legacy gpt-5-nano / prompt-v1 per-depth files as the sweep."),
            }])
        rows = []
        for lbl, spec in sorted(present.items(), key=lambda kv: kv[1]["depth"]):
            row = _row_from_summary(spec["depth"], spec["seed"], summaries[lbl])
            row["model"] = ids[lbl]["model"]
            row["prompt_version"] = ids[lbl]["prompt_version"]
            row["legacy"] = ids[lbl]["legacy"]
            rows.append(row)
        out = _sweep_from_rows(rows)
        out["legacy"] = False
        out["_gates"] = []
        return out
    return _not_run_sweep()


def mixed_depth(summaries: dict, runs: dict | None = None) -> dict:
    if REPORTED_MIXED not in summaries:
        return {"status": "not run",
                "fill_with": ("python scripts/run_eval.py --task compositional "
                              "--n-per-depth 100 --max-depth 4 --seed 29 --model openai")}
    s = summaries[REPORTED_MIXED]
    ident = _identity(runs[REPORTED_MIXED]) if runs and REPORTED_MIXED in runs else {
        "model": "gpt-5-nano", "prompt_version": "1", "legacy": True, "source": None,
    }
    per_depth = {int(d): (v["n_correct"], v["n"]) for d, v in s["by_depth"].items()}
    trend = S.depth_trend(per_depth) if len(per_depth) >= 2 else None
    return {"status": "computed", "overall": {"accuracy": s["accuracy"],
                                              "wilson_95": s["wilson_95"], "n": s["n_items"]},
            "by_depth": s["by_depth"], "trend": trend,
            "ci_separated_pairs": ([p["depths"] for p in trend["pairwise"]
                                    if not p["cis_overlap"]] if trend else []),
            "legacy": ident.get("legacy", True),
            "model": ident.get("model") or "gpt-5-nano",
            "prompt_version": ident.get("prompt_version") or "1",
            "source": ident.get("source")}


def exposure_stratification(runs: dict) -> dict:
    """§7.3. Needs pydantic to regenerate items and re-detect the renderer defect."""
    new_style = {lbl: r for lbl, r in runs.items()
                 if any("unanswerable" in p for p in r["per_item_predictions"][:1])}
    if new_style:
        out = {"status": "computed", "source": "persisted per-item flags", "sets": {}}
        for lbl, r in new_style.items():
            pips = r["per_item_predictions"]
            ex = [p for p in pips if p.get("unanswerable")]
            un = [p for p in pips if not p.get("unanswerable")]
            uk = sum(1 for p in un if p["correct"])
            out["sets"][lbl] = {
                "exposed_n": len(ex),
                "exposed_errors": sum(1 for p in ex if not p["correct"]),
                "unexposed_n": len(un),
                "unexposed_accuracy": round(uk / len(un), 4) if un else None,
                "unexposed_wilson_95": [round(v, 4) for v in S.wilson_interval(uk, len(un))] if un else None,
            }
        return out
    try:
        sys.path.insert(0, str(ROOT))
        from criterialogic.tasks.compositional import (
            generate_compositional_items,
            regenerate_reported_depth_set,
        )
        from criterialogic.taxonomy.annotate import is_unanswerable
    except Exception as e:
        return {"status": "requires pydantic",
                "detail": f"{type(e).__name__}: {e}",
                "note": ("The reported runs predate the per-item `unanswerable` flag, so "
                         "the items must be regenerated to stratify them. New runs record "
                         "the flag and need no regeneration.")}
    sets: dict = {}
    specs = [(lbl, spec["depth"], spec["n_per_depth"], spec["seed"])
             for lbl, spec in REPORTED_SWEEP.items() if lbl in runs]
    for lbl, depth, n_per, seed in specs:
        items = regenerate_reported_depth_set(depth=depth, n_per_depth=n_per, seed=seed)
        sets[lbl] = _stratify(items, runs[lbl], is_unanswerable)
    if REPORTED_MIXED in runs:
        items = generate_compositional_items(n_per_depth=100, max_depth=4, seed=29)
        sets[REPORTED_MIXED] = _stratify(items, runs[REPORTED_MIXED], is_unanswerable)
    return {"status": "computed", "source": "regenerated items", "sets": sets}


def _stratify(items, run: dict, is_unanswerable) -> dict:
    # The reported runs used renderer v1, so they are assessed as v1. New runs carry the
    # flag per item and never reach this path.
    exposed = {it.item_id for it in items if is_unanswerable(it, "1")}
    pips = run["per_item_predictions"]
    ex = [p for p in pips if p["item_id"] in exposed]
    un = [p for p in pips if p["item_id"] not in exposed]
    uk = sum(1 for p in un if p["correct"])
    return {
        "exposed_n": len(ex),
        "exposed_errors": sum(1 for p in ex if not p["correct"]),
        "exposed_error_rate": round(sum(1 for p in ex if not p["correct"]) / len(ex), 4) if ex else None,
        "unexposed_n": len(un),
        "unexposed_errors": len(un) - uk,
        "unexposed_error_rate": round((len(un) - uk) / len(un), 4) if un else None,
        "unexposed_accuracy": round(uk / len(un), 4) if un else None,
        "unexposed_wilson_95": [round(v, 4) for v in S.wilson_interval(uk, len(un))] if un else None,
    }


def taxonomy(runs: dict, summaries: dict) -> dict:
    """§7.5. Heuristic labels pooled; the human distribution is a bracket until annotated."""
    pooled: dict[str, int] = {}
    per_run: dict[str, dict] = {}
    labeller_versions = set()
    for lbl, r in runs.items():
        counts = (r.get("failure_taxonomy", {}).get("categories")
                  or r.get("failure_taxonomy_raw") or {})
        if isinstance(r.get("failure_taxonomy"), dict):
            labeller_versions.add(r["failure_taxonomy"].get("labeller_version", "1"))
        else:
            labeller_versions.add("1")
        per_run[lbl] = {"categories": counts,
                        "n_errors": summaries[lbl]["n_errors"],
                        "distinct_error_rationales": summaries[lbl]["distinct_error_rationales"]}
        for k, v in counts.items():
            pooled[k] = pooled.get(k, 0) + v
    agreement = ROOT / "results" / "agreement.json"
    human = (json.loads(agreement.read_text(encoding="utf-8")) if agreement.is_file()
             else {"status": "not run",
                   "fill_with": ("scripts/annotation_export.py then "
                                 "scripts/annotation_report.py --adjudication ...")})
    return {
        "heuristic": {"pooled": dict(sorted(pooled.items())), "per_run": per_run,
                      "labeller_versions": sorted(labeller_versions),
                      "human_only_categories": ["entity_conflation", "fabrication",
                                                "implicit_knowledge"],
                      "caveat": ("Heuristic triage labels. The manuscript's distribution is "
                                 "the human consensus; three categories are unreachable by "
                                 "any counterfactual over the logical form.")},
        "human": human,
    }


# --------------------------------------------------------------------------- #
# Integrity gates — run as part of collection so they cannot drift from it
# --------------------------------------------------------------------------- #
def gates(summaries: dict, sweep: dict, mixed: dict, sec3: dict) -> list[dict]:
    out: list[dict] = list(sweep.get("_gates") or []) + list(mixed.get("_gates") or [])

    def add(level, subject, finding, action):
        out.append({"level": level, "subject": subject, "finding": finding, "action": action})

    for lbl, s in summaries.items():
        if not s["usable_confidence_signal"]:
            add("BLOCK", lbl,
                "Every prediction carries the same confidence, so the selective-accuracy "
                "curve is flat at the overall accuracy and abstention cannot be evaluated.",
                "Report as providing no confidence signal. Do not present a curve.")
        if s["accuracy"] == 1.0:
            lo = s["wilson_95"][0]
            add("NOTE", lbl,
                f"Perfect score on n={s['n_items']}; the 95% lower bound is {lo}, so this "
                f"set cannot distinguish the system from one that is {lo:.0%} accurate.",
                "If this is the oracle baseline, label it a software-validation artifact.")
        if (s["distinct_error_rationales"] is not None and s["n_errors"] > 2
                and s["distinct_error_rationales"] < s["n_errors"]):
            add("BLOCK", lbl,
                f"{s['n_errors']} errors collapse to {s['distinct_error_rationales']} "
                f"distinct rationales — one systematic misreading replicated, not "
                f"independent observations.",
                "Report both counts; compute any taxonomy percentage over distinct modes.")
        if s["n_unanswerable_errors"]:
            add("BLOCK", lbl,
                f"{s['n_unanswerable_errors']} of {s['n_errors']} errors are on items whose "
                f"gold label rests on a fact the prompt never stated.",
                "Exclude from the taxonomy distribution and report separately (§7.3).")

    if sweep.get("status") == "computed":
        t = sweep["trend"]
        sp = t["spearman"]
        if not t["monotonic_non_increasing"]:
            add("BLOCK", "depth sweep",
                "Accuracy is not monotonically non-increasing with depth.",
                "State the observed pattern; do not assert monotonic decline.")
        if sp["p_one_sided"] > 0.05:
            add("BLOCK", "depth sweep",
                f"Depth trend p = {sp['p_one_sided']} ({sp['mode']}), not significant at 0.05.",
                "Do not claim a depth effect from this sweep alone.")
        add("NOTE", "depth sweep",
            f"Smallest attainable p with {len(sweep['rows'])} levels is "
            f"{sp['min_attainable_p']}.",
            "Report the floor wherever the p-value appears.")
        for pair in sweep["unresolved_pairs"]:
            n = pair["n_per_depth_needed"]
            add("NOTE", f"depths {tuple(pair['depths'])}",
                "Indistinguishable at this sample size."
                + ("" if n == -1 else f" Separating them needs n>={n} per depth."),
                "Do not claim a difference between these two depths individually.")
    if mixed.get("status") == "computed" and not mixed["ci_separated_pairs"]:
        add("NOTE", "mixed-depth set",
            "No pair of depths is separated at 95% confidence on the mixed set.",
            "This is the finding: the effect does not appear until beyond this depth range.")

    arm1 = (sec3 or {}).get("arm1") or {}
    if arm1.get("status") == "computed":
        if not arm1.get("coordinated_criteria"):
            add("BLOCK", "Arm 1",
                "Zero coordinated criteria: Arm 1 is entirely single-predicate at depth 0.",
                "Do not describe the coordination path as if it fires; state that Arm 1 "
                "corroborates only the shallow end of the depth curve.")
        if "exclusion" not in (arm1.get("polarity") or {}):
            add("BLOCK", "Arm 1",
                "No exclusion-polarity criteria, so criterion-level polarity is untested.",
                "State plainly that no released component exercises exclusion polarity.")
    return out


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _pct(x) -> str:
    return "—" if x is None else f"{x:.3f}"


def _ci(v) -> str:
    return "—" if not v else f"[{v[0]:.3f}, {v[1]:.3f}]"


def render(payload: dict) -> str:
    L: list[str] = []
    sec3, sweep, mixed = payload["section3"], payload["section7"]["depth_sweep"], \
        payload["section7"]["mixed_depth"]
    L += [f"# Paper data — generated {payload['generated_utc']}", "",
          "> Every number here was produced by executing code against the released",
          "> artifacts, and every aggregate is recomputed from persisted per-item",
          "> predictions rather than carried forward from a stored aggregate. Bracketed",
          "> values mark experiments that have not been run; the command that fills each",
          "> one is given beside it. Read the integrity gates at the end before quoting",
          "> anything.", ""]

    blocking = [g for g in payload["gates"] if g["level"] == "BLOCK"]
    L += [f"**{len(blocking)} blocking finding(s), "
          f"{len(payload['gates']) - len(blocking)} note(s).** See the end of this file.", ""]

    # --- Section 3 ---
    L += ["## Section 3 — dataset composition", ""]
    snap = sec3.get("snapshot")
    if snap:
        L += [f"- Snapshot `{snap['snapshot_id']}`: **{snap['n_studies']} studies**, "
              f"fetched {snap['fetched_utc']}",
              f"- Sampling frame (verbatim from the manifest): `{snap['advanced_expression']}`"]
    pool = sec3.get("atom_pool")
    if pool:
        r = pool["match_rate"]
        L += [f"- Atom pool: **{pool['n_atoms']} distinct atoms from "
              f"{pool['n_source_trials']} trials**",
              f"- Extraction matched **{pool['sentences_matched']} of "
              f"{pool['sentences_considered']} candidate sentences "
              f"({r:.1%})**" if r else "",
              f"- By section: {pool['by_section']}",
              f"- Atom first-posted range: **{pool['first_posted_range'][0]} … "
              f"{pool['first_posted_range'][1]}** (the contamination control)"]
    arm1 = sec3.get("arm1") or {}
    if arm1.get("status") == "computed":
        L += ["", "### Arm 1 (real criteria)", "",
              f"- **{arm1['n_criteria']} criteria from {arm1['n_trials']} trials**",
              f"- Mapping rate: **{arm1['segmentation'].get('mapping_rate')}**",
              f"- Polarity: **{arm1['polarity']}**",
              f"- Depth histogram: **{arm1['depth_histogram']}**",
              f"- Coordinated (compound) criteria: **{arm1['coordinated_criteria']}**",
              f"- Skipped by reason: {arm1['segmentation'].get('skipped_by_reason')}"]
    else:
        L += ["", "### Arm 1 (real criteria)", "",
              "- [N criteria from [N] trials; mapping rate [X]; polarity "
              "[inclusion]/[exclusion]; depth histogram [...]]",
              f"- Status: {arm1.get('status')}. Fill with: `{arm1.get('fill_with')}`"]
    L.append("")

    # --- 7.1 depth sweep ---
    L += ["## Section 7.1 — accuracy versus logical nesting depth", ""]
    if sweep["status"] == "computed":
        L += ["| Depth | Seed | Accuracy | 95% Wilson CI | Errors | ECE | Mean confidence | Model |",
              "|---|---|---|---|---|---|---|---|"]
        for r in sweep["rows"]:
            model = r.get("model") or sweep.get("model") or "—"
            L.append(f"| {r['depth']} | {r['seed']} | **{_pct(r['accuracy_3dp'])}** | "
                     f"{_ci(r['wilson_95'])} | {r['n_errors']} | {_pct(r['ece_3dp'])} | "
                     f"{_pct(r['mean_confidence_3dp'])} | {model} |")
        p = sweep["pooled"]
        sp = sweep["trend"]["spearman"]
        L += ["", f"Pooled: {p['n_correct']}/{p['n']} = **{_pct(p['accuracy'])}** "
                  f"{_ci(p['wilson_95'])}.",
              f"Spearman rho = **{sp['rho']}**, exact one-sided permutation p = "
              f"**{sp['p_one_sided']}** over {sp['n_permutations']} orderings "
              f"(floor {sp['min_attainable_p']}).",
              f"Monotonically non-increasing: **{sweep['trend']['monotonic_non_increasing']}**.",
              f"CI-separated pairs: {sweep['ci_separated_pairs']}.",
              "Overlapping pairs and the per-depth n that would separate them: "
              + ", ".join(f"{tuple(u['depths'])} n>={u['n_per_depth_needed']}"
                          if u["n_per_depth_needed"] != -1
                          else f"{tuple(u['depths'])} identical"
                          for u in sweep["unresolved_pairs"]) + ".", ""]
    else:
        L += [f"[not run] Fill with: `{sweep['fill_with']}`", ""]

    # --- 7.2 mixed set ---
    L += ["## Section 7.2 — the mixed-depth set", ""]
    if mixed["status"] == "computed":
        if mixed.get("legacy"):
            L += [f"**Legacy artifact.** `{mixed.get('model')}`, prompt v"
                  f"{mixed.get('prompt_version')}, source `{mixed.get('source')}`. "
                  "Not a measurement of the current run.", ""]
        L += ["| Depth | Accuracy | 95% Wilson CI | n |", "|---|---|---|---|"]
        for d, v in mixed["by_depth"].items():
            L.append(f"| {d} | {_pct(v['accuracy'])} | {_ci(v['wilson_95'])} | {v['n']} |")
        o, t = mixed["overall"], mixed["trend"]
        L += ["", f"Overall **{_pct(o['accuracy'])}** {_ci(o['wilson_95'])} on n={o['n']}."]
        if t:
            L.append(f"Spearman rho = {t['spearman']['rho']}, exact p = "
                     f"{t['spearman']['p_one_sided']}. CI-separated pairs: "
                     f"{mixed['ci_separated_pairs'] or 'none'}.")
        L.append("")
    else:
        L += [f"[not run] Fill with: `{mixed['fill_with']}`", ""]

    # --- 7.3 exposure ---
    exp = payload["section7"]["exposure"]
    L += ["## Section 7.3 — exposure to the renderer defect", ""]
    if exp["status"] == "computed":
        L += [f"Source: {exp['source']}.", "",
              "| Set | Exposed n | Errors in exposed | Unexposed n | Unexposed accuracy | 95% CI |",
              "|---|---|---|---|---|---|"]
        for lbl, v in exp["sets"].items():
            short = lbl.replace("compositional_", "").replace("::openai", "")
            L.append(f"| {short} | {v['exposed_n']} | {v['exposed_errors']} | "
                     f"{v['unexposed_n']} | {_pct(v['unexposed_accuracy'])} | "
                     f"{_ci(v['unexposed_wilson_95'])} |")
        L.append("")
    else:
        L += [f"[{exp['status']}] {exp.get('detail', '')}", exp.get("note", ""), ""]

    # --- 7.4 calibration ---
    L += ["## Section 7.4 — calibration and abstention", "",
          "| Set | ECE | Mean conf. | @10% | @30% | @50% | @100% | Usable signal |",
          "|---|---|---|---|---|---|---|---|"]
    for lbl, s in payload["runs"].items():
        sa = s["selective_accuracy"]
        tag = " *(legacy)*" if s.get("legacy") else ""
        L.append(f"| {lbl}{tag} | {_pct(s['ece_3dp'])} | {_pct(s['mean_confidence_3dp'])} | "
                 f"{sa.get('10%')} | {sa.get('30%')} | {sa.get('50%')} | {sa.get('100%')} | "
                 f"{'yes' if s['usable_confidence_signal'] else '**no**'} |")
    L.append("")

    # --- 7.5 taxonomy ---
    tax = payload["section7"]["taxonomy"]
    L += ["## Section 7.5 — failure taxonomy", "",
          f"Heuristic labeller version(s) {tax['heuristic']['labeller_versions']}. "
          f"{tax['heuristic']['caveat']}", "",
          "| Category | Pooled errors |", "|---|---|"]
    for k, v in tax["heuristic"]["pooled"].items():
        L.append(f"| {k} | {v} |")
    L += ["", f"Human-only categories, unreachable by the labeller: "
              f"{tax['heuristic']['human_only_categories']}.", ""]
    if tax["human"].get("status") == "not run":
        L += ["**Human annotation: [not run].**", "",
              "To be reported: consensus distribution [...]; Cohen's kappa [k] with 95% CI",
              "[lo, hi]; percent agreement [x]; per-category kappa [...]; kappa by arm",
              "(compositional [k], real criteria [k]); fraction flagged as requiring",
              "clinical judgement [x] with kappa flagged [k] versus not [k]; disagreements",
              "adjudicated [n], of which clinical [n]; automatic-versus-consensus kappa [k]",
              "with [n] agreement-impossible items.", "",
              f"Fill with: `{tax['human']['fill_with']}`", ""]
    else:
        L += ["### Human annotation", "", "```json",
              json.dumps(tax["human"], indent=2)[:4000], "```", ""]

    # --- gates ---
    L += ["## Integrity gates", ""]
    if not payload["gates"]:
        L.append("No findings.")
    for g in payload["gates"]:
        L += [f"### [{g['level']}] {g['subject']}", "", g["finding"], "",
              f"**Action.** {g['action']}", ""]

    # --- provenance ---
    L += ["## Provenance", "", "```json",
          json.dumps(payload["provenance"], indent=2), "```"]
    return "\n".join(x for x in L if x is not None)


# --------------------------------------------------------------------------- #
# Verification against the manuscript
# --------------------------------------------------------------------------- #
#: A depth row in the manuscript's 7.1 table. The seed column is optional, because the
#: manuscript prints six columns and results/paper_data.md prints seven; verification must
#: work on whichever the author pasted rather than on one house style.
_DEPTH_ROW = re.compile(
    r"^\|\s*(\d)\s*\|(?:\s*\d+\s*\|)?\s*\*\*([\d.]+)\*\*\s*\|\s*\[([\d.]+),\s*([\d.]+)\]\s*\|"
    r"\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", re.M)
#: Accepts the word or the typeset symbol, and a hyphen-minus or a true minus sign.
_RHO = re.compile(r"Spearman (?:rho|\u03c1)\s*=\s*\*\*[\u2212-]?([\d.]+)\*\*")
_P = re.compile(r"permutation\s*\n?\s*\*?\*?p\*?\*?\s*=\s*\*\*([\d.]+)\*\*")
#: 3.2 composition. Bold optional, and the two counts may sit either side of a line break.
_ARM1_COMPOSITION = re.compile(
    r"\*{0,2}(\d+)\*{0,2}\s+criteria\s+from\s+\*{0,2}(\d+)\*{0,2}\s+trials")
#: 7.6 real-criteria arm. micro-F1 equals accuracy on this arm; either wording is accepted.
_MICRO_F1 = re.compile(r"micro-F1\s*\*{0,2}([\d.]+)\*{0,2}")
#: 7.7 ablations. The spread between the best and worst depth under one fixed prompt.
#: Both orders occur in drafts: "an accuracy range of 0.433" and "a 0.433 accuracy range".
_ACC_RANGE = re.compile(
    r"accuracy\s+range\s+of\s*\*{0,2}(0\.\d+)\*{0,2}"
    r"|\*{0,2}(0\.\d+)\*{0,2}\s+accuracy\s+range")


def _section(text: str, number: str) -> str:
    """Return the body of the section whose heading contains `number`.

    Scoping is not cosmetic. Section 2 cites another system's micro-F1 and another
    corpus's criteria-and-trials counts, so an unscoped search checks the paper's
    background against this paper's artifacts and reports a mismatch that is not one.
    Falls back to the whole text when no heading matches, so a numbers extract with no
    headings still verifies.
    """
    heading = re.compile(rf"^#{{1,6}}\s.*\b{re.escape(number)}\b.*$", re.M)
    m = heading.search(text)
    if not m:
        return text
    nxt = re.compile(r"^#{1,6}\s", re.M).search(text, m.end())
    return text[m.end():nxt.start() if nxt else len(text)]


def verify(paper: Path, payload: dict) -> list[str]:
    """Diff the numbers written in the manuscript against the computed ones."""
    if not paper.is_file():
        return [f"Paper not found at {paper}"]
    text = paper.read_text(encoding="utf-8")
    problems: list[str] = []
    sweep = payload["section7"]["depth_sweep"]
    if sweep["status"] != "computed":
        return ["Depth sweep has not been run; nothing to verify against."]

    computed = {r["depth"]: r for r in sweep["rows"]}
    found: dict[int, tuple] = {}
    for m in _DEPTH_ROW.finditer(text):
        depth = int(m.group(1))
        if depth in computed and depth not in found:
            found[depth] = (float(m.group(2)), float(m.group(3)), float(m.group(4)),
                            int(m.group(5)), float(m.group(6)), float(m.group(7)))
    for depth, r in computed.items():
        if depth not in found:
            problems.append(f"depth {depth}: no matching row found in the paper")
            continue
        acc, lo, hi, errs, ece, conf = found[depth]
        for name, got, want in (("accuracy", acc, r["accuracy_3dp"]),
                                ("CI lower", lo, r["wilson_95"][0]),
                                ("CI upper", hi, r["wilson_95"][1]),
                                ("ECE", ece, r["ece_3dp"]),
                                ("mean confidence", conf, r["mean_confidence_3dp"])):
            # Tight: the manuscript quotes these to three decimals and so does the
            # generator, so anything beyond half a unit in the last place is real drift.
            if abs(got - want) > 0.0006:
                problems.append(f"depth {depth} {name}: paper says {got}, artifacts say {want}")
        if errs != r["n_errors"]:
            problems.append(f"depth {depth} errors: paper says {errs}, artifacts say {r['n_errors']}")

    rho_m, p_m = _RHO.search(text), _P.search(text)
    sp = sweep["trend"]["spearman"]
    if rho_m and abs(float(rho_m.group(1)) - abs(sp["rho"])) > 0.002:
        problems.append(f"Spearman rho: paper says {rho_m.group(1)}, artifacts say {sp['rho']}")
    if p_m and abs(float(p_m.group(1)) - sp["p_one_sided"]) > 0.002:
        problems.append(f"permutation p: paper says {p_m.group(1)}, "
                        f"artifacts say {round(sp['p_one_sided'], 4)}")
    if not rho_m:
        problems.append("Could not find the Spearman rho claim in the paper to check.")

    # ---- 3.2 dataset composition -------------------------------------------
    # Absent is not an error: a numbers extract legitimately omits section 3. Present but
    # wrong is, because these two counts are the ones the whole of Arm 1 is scaled from.
    arm1 = payload["section3"]["arm1"]
    comp_m = _ARM1_COMPOSITION.search(_section(text, "3.2"))
    if comp_m and arm1.get("status") == "computed":
        for name, got, want in (("criteria", int(comp_m.group(1)), arm1["n_criteria"]),
                                ("trials", int(comp_m.group(2)), arm1["n_trials"])):
            if got != want:
                problems.append(f"3.2 {name}: paper says {got}, artifacts say {want}")

    # ---- 7.6 real-criteria arm ---------------------------------------------
    # micro-F1 == accuracy on this arm (every item carries one label), so the accuracy
    # already recomputed from the per-item predictions is the reference.
    arm1_run = payload["runs"].get("real_criteria::openai")
    f1_m = _MICRO_F1.search(_section(text, "7.6"))
    if f1_m and arm1_run:
        got, want = float(f1_m.group(1)), arm1_run["accuracy_3dp"]
        if abs(got - want) > 0.0006:
            problems.append(f"7.6 micro-F1: paper says {got}, artifacts say {want}")

    # ---- 7.7 accuracy range across depths -----------------------------------
    range_m = _ACC_RANGE.search(_section(text, "7.7"))
    if range_m:
        accs = [r["accuracy"] for r in sweep["rows"]]
        want = round(max(accs) - min(accs), 3)
        got = float(range_m.group(1) or range_m.group(2))
        if abs(got - want) > 0.0006:
            problems.append(f"7.7 accuracy range: paper says {got}, artifacts say {want}")

    return problems


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--paper", default=str(ROOT / "results" / "verify_extract.md"),
                    help="File --verify diffs against. Defaults to the committed numbers extract.")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--verify", action="store_true",
                    help="Diff the numbers extract against the artifacts and exit non-zero on a mismatch.")
    ap.add_argument("--run", action="store_true",
                    help="Run the offline arms first, so their rows are present.")
    args = ap.parse_args()

    results_dir = Path(args.results)
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        try:
            sys.path.insert(0, str(ROOT))
            from criterialogic.data.paths import data_dir as _dd
            data_dir = _dd()
        except Exception:
            data_dir = ROOT / "data"

    if args.run:
        sys.path.insert(0, str(ROOT))
        from criterialogic.cli import main as cli_main
        argv = sys.argv
        sys.argv = ["criterialogic-eval", "--outdir", str(results_dir)]
        try:
            cli_main()
        finally:
            sys.argv = argv

    runs = load_runs(results_dir)
    if not runs:
        print(f"No runs with per-item predictions under {results_dir}. "
              f"Run scripts/run_eval.py first, or pass --run.", file=sys.stderr)
        return 1
    summaries = {lbl: summarise_run(lbl, r) for lbl, r in runs.items()}
    sec3 = section3(data_dir)
    sweep = depth_sweep(summaries, runs)
    mixed = mixed_depth(summaries, runs)
    current = runs.get(CURRENT_SWEEP_LABEL, {})
    current_model = current.get("model") if isinstance(current.get("model"), dict) else {}
    if (current_model.get("effective_temperature") == 0.0
            and not current_model.get("dropped_parameters")):
        repro_note = (
            "Item sets, gold labels and prompts are deterministic. For the current "
            "gpt-4o-mini / prompt v2 run, requested temperature 0.0 was applied "
            "(dropped_parameters empty). Completions are not redistributed; the "
            "per-item predictions are the record of the run.")
    else:
        repro_note = (
            "Item sets, gold labels and prompts are deterministic. Model completions "
            "are not redistributed. The per-item predictions are the record of the run.")
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provenance": {
            "results_dir": _repo_rel(results_dir),
            "data_dir": _repo_rel(data_dir),
            "runs_loaded": {lbl: r.get("source") for lbl, r in runs.items()},
            "inference_parameters": {lbl: r.get("inference") or r.get("model")
                                     for lbl, r in runs.items()},
            "reproducibility_note": repro_note,
        },
        "runs": summaries,
        "section3": sec3,
        "section7": {
            "depth_sweep": sweep,
            "mixed_depth": mixed,
            "exposure": exposure_stratification(runs),
            "taxonomy": taxonomy(runs, summaries),
        },
    }
    payload["gates"] = gates(summaries, sweep, mixed, sec3)

    if args.verify:
        problems = verify(Path(args.paper), payload)
        if problems:
            print(f"{len(problems)} mismatch(es) between the manuscript and the artifacts:")
            for p in problems:
                print(f"  - {p}")
            return len(problems)
        print("Manuscript matches the artifacts on every checked figure.")
        return 0

    out_json = Path(args.out_json or results_dir / "paper_data.json")
    out_md = Path(args.out_md or results_dir / "paper_data.md")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_md.write_text(render(payload) + "\n", encoding="utf-8")
    blocking = sum(1 for g in payload["gates"] if g["level"] == "BLOCK")
    print(f"[wrote] {out_json}")
    print(f"[wrote] {out_md}")
    print(f"  {len(runs)} run(s); {blocking} blocking gate(s), "
          f"{len(payload['gates']) - blocking} note(s)")
    print("  verify the manuscript against these with: "
          "python scripts/collect_paper_data.py --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
