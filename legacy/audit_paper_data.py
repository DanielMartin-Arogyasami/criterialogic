#!/usr/bin/env python3
"""Audit results/paper_data.json for integrity problems before anything is written into the paper.

Standard library only. Does not import criterialogic. Run it anywhere the JSON is.

    python audit_paper_data.py [path/to/paper_data.json]

Writes results/AUDIT.md, results/audit.json, and results/selective_accuracy_corrected.json.

Checks performed
----------------
C1  constant-confidence detection      -> selective-accuracy curves that are sort-order artifacts
C2  corrected selective-accuracy       -> tie-aware expected accuracy, recomputed where possible
C3  ceiling / saturation detection     -> tasks a model has saturated, with Wilson CIs
C4  duplicate-rationale clustering     -> distinct failure modes vs raw error count
C5  suspect item detection             -> errors whose rationale asserts the gold predicate
C6  depth-trend statistics             -> Wilson CIs, Spearman, permutation p, power
C7  inference-parameter contradictions -> run records vs reproducibility block
C8  discrepancy-list sync              -> JSON list vs referenced DISCREPANCIES.md entries
C9  polarity coverage                  -> whether any exclusion criterion exists at all
C10 structural coverage                -> nesting-depth distribution of the matching criteria
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

Z95 = 1.959963984540054
Z80 = 0.8416212335729143  # one-sided z for 80% power


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #

def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval. Correct at k=0 and k=n, unlike the normal approximation."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rho with average ranks for ties."""
    def rank(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx and dy else 0.0


def spearman_exact_p(xs: list[float], ys: list[float]) -> float:
    """Two-sided exact permutation p-value. Enumerable for the small n of a depth curve."""
    n = len(xs)
    if n > 8:
        return float("nan")
    obs = abs(spearman(xs, ys))
    perms = list(permutations(ys))
    hits = sum(1 for p in perms if abs(spearman(xs, list(p))) >= obs - 1e-12)
    return hits / len(perms)


def n_per_group_for(p1: float, p2: float, alpha_z: float = Z95, beta_z: float = Z80) -> int:
    """Two-proportion sample size per group at 80% power, 5% two-sided."""
    d = abs(p1 - p2)
    if d < 1e-9:
        return -1
    var = p1 * (1 - p1) + p2 * (1 - p2)
    return math.ceil((alpha_z + beta_z) ** 2 * var / (d * d))


def ci_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])


# --------------------------------------------------------------------------- #
# corrected selective accuracy
# --------------------------------------------------------------------------- #

def selective_accuracy_tie_aware(conf: list[float], correct: list[bool]) -> list[dict]:
    """Expected selective accuracy under uniform random tie-breaking.

    The naive implementation sorts by confidence and slices. When many items share a
    confidence value the slice boundary falls inside a tie group, so the reported curve
    depends on the incidental order of the list rather than on the model's confidence.
    This returns the exact expectation over random orderings within each tie group.
    """
    n = len(conf)
    if n == 0:
        return []
    idx = sorted(range(n), key=lambda i: -conf[i])

    groups: list[list[int]] = []
    for i in idx:
        if groups and conf[groups[-1][0]] == conf[i]:
            groups[-1].append(i)
        else:
            groups.append([i])

    out: list[dict] = []
    done = 0
    correct_so_far = 0.0
    for g in groups:
        g_correct = sum(1 for i in g if correct[i])
        rate = g_correct / len(g)
        for j in range(1, len(g) + 1):
            k = done + j
            exp_correct = correct_so_far + j * rate
            out.append({
                "coverage": round(k / n, 6),
                "n_covered": k,
                "expected_accuracy": round(exp_correct / k, 6),
                "threshold_confidence": conf[g[0]],
                "inside_tie_group": len(g) > 1 and j < len(g),
            })
        done += len(g)
        correct_so_far += g_correct
    return out


def sample_curve(curve: list[dict], levels: list[float]) -> dict:
    out = {}
    for c in levels:
        pt = next((p for p in curve if p["coverage"] >= c - 1e-9), None)
        out[f"{int(c * 100)}%"] = pt["expected_accuracy"] if pt else None
    return out


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def headline(metrics: dict) -> tuple[str, float] | tuple[None, None]:
    for key in ("overall_accuracy", "overall_micro_f1"):
        if key in metrics:
            return key, metrics[key]
    return None, None


def n_items(run: dict) -> int:
    return run.get("n_items") or run.get("metrics", {}).get("n_items") or 0


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #

def check_constant_confidence(runs: dict) -> list[dict]:
    """ECE == |accuracy - mean_confidence| exactly implies every prediction shares one bin."""
    findings = []
    for name, run in runs.items():
        _, acc = headline(run.get("metrics", {}))
        mc = run.get("mean_confidence")
        ece = run.get("calibration", {}).get("ece")
        if acc is None or mc is None or ece is None:
            continue
        gap = abs(acc - mc)
        constant = abs(gap - ece) < 1e-9
        curve = run.get("selective_accuracy") or {}
        vals = [v for v in curve.values() if v is not None]
        spread = (max(vals) - min(vals)) if vals else 0.0
        if constant and spread > 1e-6:
            findings.append({
                "run": name,
                "severity": "HIGH",
                "mean_confidence": mc,
                "accuracy": acc,
                "ece": ece,
                "reported_curve_spread": round(spread, 4),
                "problem": (
                    "Every prediction carries the same confidence, so ranking by confidence is "
                    "arbitrary, yet the reported selective-accuracy curve varies by "
                    f"{spread:.3f}. That variation is list order, not confidence. The curve is "
                    "flat at the overall accuracy and the model has no usable abstention signal."
                ),
                "action": "Do not report this curve in Sec. 7.4. Report the model as providing no confidence signal.",
            })
        elif constant:
            findings.append({
                "run": name,
                "severity": "NOTE",
                "mean_confidence": mc,
                "accuracy": acc,
                "ece": ece,
                "problem": "Single confidence bin; ECE here is just |accuracy - constant confidence|.",
                "action": "State that ECE is degenerate for this model rather than presenting it as calibration.",
            })
    return findings


def check_saturation(runs: dict) -> list[dict]:
    findings = []
    for name, run in runs.items():
        key, acc = headline(run.get("metrics", {}))
        n = n_items(run)
        if acc is None or not n:
            continue
        if acc >= 0.999:
            lo, hi = wilson(n, n)
            findings.append({
                "run": name,
                "severity": "HIGH" if "rule_based" not in name else "EXPECTED",
                "metric": key,
                "value": acc,
                "n": n,
                "wilson_95": [round(lo, 4), round(hi, 4)],
                "problem": (
                    f"Perfect score on n={n}. The 95% CI lower bound is {lo:.3f}, so this set "
                    f"cannot distinguish the system from one that is {lo * 100:.0f}% accurate. "
                    "The task does not discriminate at this size."
                ),
                "n_needed_to_detect_95pct": n_per_group_for(1.0, 0.95),
                "n_needed_to_detect_90pct": n_per_group_for(1.0, 0.90),
                "action": (
                    "Software-validation artifact; already disclosed."
                    if "rule_based" in name else
                    "Harden the task (greater depth, more operands, adversarial distractors) "
                    "or enlarge n before making any claim from this row."
                ),
            })
    return findings


def check_error_independence(runs: dict) -> list[dict]:
    findings = []
    for name, run in runs.items():
        errs = run.get("error_items") or []
        if not errs:
            continue
        by_rationale = Counter(e.get("rationale", "") for e in errs)
        by_prefix = defaultdict(list)
        for e in errs:
            by_prefix[":".join(str(e.get("item_id", "")).split(":")[:2])].append(e)
        distinct = len(by_rationale)
        if distinct < len(errs):
            findings.append({
                "run": name,
                "severity": "HIGH",
                "raw_error_count": len(errs),
                "distinct_rationales": distinct,
                "largest_cluster": max(by_rationale.values()),
                "clusters": [
                    {"count": c, "rationale": r[:160]}
                    for r, c in by_rationale.most_common() if c > 1
                ],
                "errors_per_criterion": {k: len(v) for k, v in sorted(by_prefix.items())},
                "problem": (
                    f"{len(errs)} error items collapse to {distinct} distinct rationales. These are "
                    "not independent observations; one systematic misreading is replicated across "
                    "items. Reporting the raw count as a taxonomy distribution overstates the evidence."
                ),
                "action": (
                    "Report both counts in Sec. 7.3: raw errors and distinct failure modes. "
                    "The taxonomy percentage must be computed over distinct modes."
                ),
            })
    return findings


def check_suspect_items(runs: dict) -> list[dict]:
    """An error whose rationale asserts the gold predicate is present is a candidate item bug."""
    assertive = ("is present", "are present", "is documented", "present,", "indicating")
    findings = []
    for name, run in runs.items():
        for e in run.get("error_items") or []:
            r = (e.get("rationale") or "").lower()
            if e.get("gold") == "not_met" and e.get("predicted") == "met" and any(a in r for a in assertive):
                findings.append({
                    "run": name,
                    "severity": "HIGH",
                    "item_id": e.get("item_id"),
                    "gold": e.get("gold"),
                    "predicted": e.get("predicted"),
                    "confidence": e.get("confidence"),
                    "assigned_category": e.get("category"),
                    "rationale": e.get("rationale"),
                    "problem": (
                        "The model asserts the criterion predicate is present in the record while "
                        "gold says not met. Either the generated record does state it (item is "
                        "mislabelled), or it is underspecified and the item is unanswerable. Both "
                        "are generator bugs being scored as reasoning failures."
                    ),
                    "action": "Dump the full record for this item and adjudicate before attributing the error to the model.",
                })
    return findings


def check_depth_trend(runs: dict) -> list[dict]:
    findings = []
    for name, run in runs.items():
        bd = run.get("metrics", {}).get("by_depth")
        if not bd:
            continue
        depths, accs, ns, cis = [], [], [], []
        for d in sorted(bd, key=lambda x: int(x)):
            v = bd[d]
            depths.append(int(d))
            accs.append(v["accuracy"])
            ns.append(v["n"])
            cis.append(wilson(round(v["accuracy"] * v["n"]), v["n"]))
        if len(depths) < 2:
            continue
        rho = spearman([float(d) for d in depths], accs)
        p = spearman_exact_p([float(d) for d in depths], accs)
        monotonic = all(accs[i] >= accs[i + 1] for i in range(len(accs) - 1))
        pairs = []
        for i in range(len(depths)):
            for j in range(i + 1, len(depths)):
                pairs.append({
                    "depths": [depths[i], depths[j]],
                    "accuracies": [accs[i], accs[j]],
                    "cis_overlap": ci_overlap(cis[i], cis[j]),
                    "n_per_depth_needed": n_per_group_for(accs[i], accs[j]),
                })
        findings.append({
            "run": name,
            "severity": "NOTE" if monotonic else "HIGH",
            "depths": depths,
            "accuracies": accs,
            "n_per_depth": ns,
            "wilson_95": [[round(a, 4), round(b, 4)] for a, b in cis],
            "spearman_rho": round(rho, 4),
            "exact_permutation_p": round(p, 4) if p == p else None,
            "monotonic_decline": monotonic,
            "pairwise": pairs,
            "problem": (
                "Accuracy is monotonically non-increasing with depth."
                if monotonic else
                "Accuracy is NOT monotonically decreasing with depth. Sec. 7.2 states monotonic "
                "decline as the hypothesis; this run does not support it."
            ),
            "action": (
                "Report rho with the exact p-value and per-depth Wilson intervals. Where the "
                "intervals overlap, state that the depths are indistinguishable at this n and "
                "give the n-per-depth required."
            ),
        })
    return findings


def check_inference_params(data: dict) -> list[dict]:
    findings = []
    repro = data.get("reproducibility", {})
    effective = str(repro.get("llm_temperature_effective", "")).lower()
    requested = repro.get("llm_temperature_requested")
    if "none" in effective or "default" in effective:
        for name, run in data.get("runs", {}).items():
            m = run.get("model", {})
            if "temperature" in m:
                findings.append({
                    "run": name,
                    "severity": "HIGH",
                    "run_record_says": {"temperature": m["temperature"]},
                    "reproducibility_says": {
                        "requested": requested, "effective": repro.get("llm_temperature_effective")
                    },
                    "problem": (
                        "The per-run model record asserts a temperature that was never applied. "
                        "Anyone reading the JSON (rather than the prose banner) gets a false "
                        "inference parameter, which is exactly what Sec. 6 promises to report."
                    ),
                    "action": (
                        "Replace with requested_temperature / effective_temperature / "
                        "dropped_parameters recorded per call at request time."
                    ),
                })
    return findings


def check_discrepancy_sync(data: dict) -> list[dict]:
    listed = data.get("discrepancies", [])
    referenced = 0
    blob = json.dumps(data)
    for i in range(1, 20):
        if f"DISCREPANCIES.md entry {i}" in blob:
            referenced = max(referenced, i)
    if referenced > len(listed):
        return [{
            "severity": "MEDIUM",
            "entries_in_json": len(listed),
            "highest_entry_referenced": referenced,
            "problem": (
                f"The JSON carries {len(listed)} discrepancies but text inside it refers to entry "
                f"{referenced} of results/DISCREPANCIES.md. The machine-readable list is behind the "
                "prose one, so an automated reader sees fewer known problems than exist."
            ),
            "action": "Make DISCREPANCIES.md generated from the JSON list, not maintained beside it.",
        }]
    return []


def check_polarity_and_structure(data: dict) -> list[dict]:
    findings = []
    detail = data.get("dataset_composition", {}).get("n2c2_criteria_detail", [])
    if not detail:
        return findings
    pol = Counter(c.get("polarity") for c in detail)
    if len(pol) == 1:
        only = next(iter(pol))
        findings.append({
            "severity": "HIGH",
            "polarity_distribution": dict(pol),
            "problem": (
                f"All {len(detail)} matching criteria are encoded polarity={only}. There is no "
                "exclusion criterion anywhere in the task, so criterion-level polarity cannot be "
                "tested. Sec. 3.1 justifies keeping polarity distinct from negation in order to "
                "'test exclusion semantics directly', and negation/polarity is taxonomy category 1."
            ),
            "action": (
                "Either add exclusion-polarity items (the ClinicalTrials.gov pool has real "
                "exclusion criteria) or state plainly in Sec. 3.1 and the limitations that no "
                "released component exercises exclusion polarity in v0.1."
            ),
        })
    depths = Counter(c.get("depth") for c in detail)
    shallow = sum(v for k, v in depths.items() if k is not None and k <= 0)
    if shallow / max(len(detail), 1) >= 0.5:
        findings.append({
            "severity": "MEDIUM",
            "depth_distribution": dict(sorted(depths.items())),
            "problem": (
                f"{shallow} of {len(detail)} matching criteria are single atoms at depth 0. The "
                "matching task carries almost no compositional structure, so all compositional "
                "evidence rests on the synthetic task."
            ),
            "action": "Say so explicitly in Sec. 3.3 rather than letting the task table imply otherwise.",
        })
    return findings


def check_untested_cells(data: dict) -> list[dict]:
    """Model x dataset cells that exist for some models but were never run for others."""
    runs = data.get("runs", {})
    by_task, by_model = defaultdict(set), defaultdict(set)
    for name in runs:
        if "::" not in name:
            continue
        task, model = name.split("::", 1)
        by_task[task].add(model)
        by_model[model].add(task)
    all_models = set(m for ms in by_task.values() for m in ms)
    findings = []
    for task, models in sorted(by_task.items()):
        missing = sorted(all_models - models)
        if missing:
            findings.append({
                "severity": "HIGH",
                "dataset": task,
                "models_run": sorted(models),
                "models_missing": missing,
                "problem": (
                    f"Dataset '{task}' was never evaluated for: {', '.join(missing)}. "
                    "The leaderboard has a hole, and if this is the larger or deeper set it is "
                    "precisely the cell most likely to be informative."
                ),
                "action": f"Run {', '.join(missing)} on '{task}' before drafting Sec. 7.1 or 7.2.",
            })
    return findings


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #

def build_report(data: dict, audit: dict) -> str:
    L: list[str] = []
    A = L.append
    counts = Counter()
    for group in audit["findings"].values():
        for f in group:
            counts[f.get("severity", "NOTE")] += 1

    A("# CriteriaLogic — integrity audit of `paper_data.json`")
    A("")
    A(f"Audited {audit['audited_file']} · generated {audit['generated_utc']}")
    A("")
    A(f"**{counts['HIGH']} HIGH · {counts['MEDIUM']} MEDIUM · {counts['NOTE']} NOTE · "
      f"{counts['EXPECTED']} EXPECTED (disclosed artifacts)**")
    A("")
    A("> Every HIGH finding blocks a specific claim in the manuscript. Nothing below is a "
      "suggestion about presentation; each one is a place where the current data would not "
      "support the sentence the paper wants to write.")
    A("")

    titles = {
        "constant_confidence": "C1 — Constant-confidence models and fabricated abstention curves",
        "saturation": "C3 — Ceiling effects: tasks that no longer discriminate",
        "error_independence": "C4 — Error counts vs. distinct failure modes",
        "suspect_items": "C5 — Errors that are probably item bugs, not model failures",
        "depth_trend": "C6 — Depth-trend statistics",
        "untested_cells": "C7 — Missing leaderboard cells",
        "inference_params": "C8 — Inference-parameter contradictions",
        "discrepancy_sync": "C9 — Discrepancy list synchronisation",
        "polarity_structure": "C10 — Polarity and structural coverage",
    }

    for key, title in titles.items():
        items = audit["findings"].get(key, [])
        A(f"## {title}")
        A("")
        if not items:
            A("No findings.")
            A("")
            continue
        for f in items:
            head = f.get("run") or f.get("dataset") or f.get("item_id") or "corpus-level"
            A(f"### [{f['severity']}] `{head}`")
            A("")
            A(f["problem"])
            A("")
            for k, v in f.items():
                if k in ("problem", "action", "severity", "run", "dataset"):
                    continue
                if isinstance(v, (dict, list)):
                    v = json.dumps(v)
                A(f"- `{k}`: {v}")
            A("")
            A(f"**Action.** {f['action']}")
            A("")

    A("## Corrected selective-accuracy curves")
    A("")
    A("Recomputed tie-aware where per-item confidences were recoverable; otherwise the run is "
      "listed as needing a rerun with per-item predictions persisted.")
    A("")
    for name, v in audit["corrected_selective_accuracy"].items():
        A(f"- `{name}`: {v}")
    A("")

    A("## What this audit cannot see")
    A("")
    A("- Per-item confidences and correctness are not stored in `paper_data.json`, only aggregates "
      "and the error subset. C1 is detected algebraically rather than recomputed. Persist per-item "
      "predictions so the corrected curve can be computed directly.")
    A("- Item text and patient records are absent, so C5 flags candidates but cannot adjudicate them.")
    A("- Nothing here validates the gold labels themselves.")
    A("")
    return "\n".join(L)


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results/paper_data.json")
    if not src.exists():
        sys.exit(f"[error] not found: {src}\nUsage: python audit_paper_data.py [path/to/paper_data.json]")

    data = json.loads(src.read_text(encoding="utf-8"))
    runs = data.get("runs", {})

    from datetime import datetime, timezone
    audit = {
        "audited_file": str(src),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "findings": {
            "constant_confidence": check_constant_confidence(runs),
            "saturation": check_saturation(runs),
            "error_independence": check_error_independence(runs),
            "suspect_items": check_suspect_items(runs),
            "depth_trend": check_depth_trend(runs),
            "untested_cells": check_untested_cells(data),
            "inference_params": check_inference_params(data),
            "discrepancy_sync": check_discrepancy_sync(data),
            "polarity_structure": check_polarity_and_structure(data),
        },
        "corrected_selective_accuracy": {},
    }

    # Corrected curves: only computable where per-item predictions were persisted.
    for name, run in runs.items():
        preds = run.get("per_item_predictions")
        if preds:
            conf = [p["confidence"] for p in preds]
            corr = [bool(p["correct"]) for p in preds]
            curve = selective_accuracy_tie_aware(conf, corr)
            audit["corrected_selective_accuracy"][name] = sample_curve(
                curve, [0.1 * i for i in range(1, 11)]
            )
        else:
            _, acc = headline(run.get("metrics", {}))
            mc = run.get("mean_confidence")
            ece = run.get("calibration", {}).get("ece")
            if acc is not None and mc is not None and ece is not None and abs(abs(acc - mc) - ece) < 1e-9:
                audit["corrected_selective_accuracy"][name] = {
                    "status": "DEGENERATE — single confidence bin; true curve is flat",
                    "flat_value": round(acc, 4),
                }
            else:
                audit["corrected_selective_accuracy"][name] = {
                    "status": "NOT RECOMPUTABLE — persist per_item_predictions "
                              "[{item_id, confidence, correct}] and rerun this audit"
                }

    out = Path("results")
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (out / "AUDIT.md").write_text(build_report(data, audit), encoding="utf-8")
    (out / "selective_accuracy_corrected.json").write_text(
        json.dumps(audit["corrected_selective_accuracy"], indent=2), encoding="utf-8"
    )

    counts = Counter()
    for group in audit["findings"].values():
        for f in group:
            counts[f.get("severity", "NOTE")] += 1
    print(f"[wrote] {out / 'AUDIT.md'}")
    print(f"[wrote] {out / 'audit.json'}")
    print(f"[wrote] {out / 'selective_accuracy_corrected.json'}")
    print(f"[summary] HIGH={counts['HIGH']} MEDIUM={counts['MEDIUM']} "
          f"NOTE={counts['NOTE']} EXPECTED={counts['EXPECTED']}")
    if counts["HIGH"]:
        print("[gate] HIGH findings present — do not fill Section 7 until each is resolved or disclosed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
