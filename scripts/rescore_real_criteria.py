#!/usr/bin/env python3
"""Re-score Arm 1 on the verified subset, from the released predictions. No model calls.

    python scripts/rescore_real_criteria.py

Reads ``annotation/arm1_verification.csv`` — one keep/drop verdict per criterion, on
whether the mapped form expresses the criterion as written (see
annotation/ARM1_VERIFICATION.md) — rebuilds the Arm 1 items exactly as the released run
did (seed 29, two synthetic patients per criterion), checks every gold label against the
released result file, and reports accuracy on three nested subsets:

1. all items — reproduces the released figure (0.935);
2. verified criteria — items whose criterion has verdict ``keep``;
3. verified criteria, label not resting on the currency convention — additionally
   drops items in which a leaf with no time qualifier has a fact that is present but
   recorded as not current. The oracle counts such a leaf as met; the prompt renders it
   as "present, not currently active"; and the criterion text does not settle which
   reading is meant. This is the headline subset.

It then recomputes inter-annotator agreement with the Arm 1 errors outside subset 3
removed, since those are not established model failures.

Writes results/real_criteria_verified.{json,md}.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from criterialogic.data.harmonize import harmonized_real_criteria
from criterialogic.metrics.stats import expected_calibration_error, wilson_interval
from criterialogic.metrics.structure import balanced_accuracy, currency_ambiguous_leaves
from criterialogic.tasks.real_criteria import generate_real_criteria_items
from criterialogic.taxonomy.reliability import agreement_report, load_annotations

VERDICTS = ("keep", "drop")


def load_verdicts(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            v = (row.get("verdict") or "").strip().lower()
            if v not in VERDICTS:
                raise SystemExit(f"{path}: {row.get('criterion_id')!r} has verdict {v!r}; "
                                 f"use one of {VERDICTS}.")
            out[row["criterion_id"].strip()] = v
    return out


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    k = sum(r["correct"] for r in rows)
    lo, hi = wilson_interval(k, n)

    def f1(cls: bool) -> float:
        tp = sum(1 for r in rows if r["pred"] == cls and r["gold"] == cls)
        fp = sum(1 for r in rows if r["pred"] == cls and r["gold"] != cls)
        fn = sum(1 for r in rows if r["pred"] != cls and r["gold"] == cls)
        return 2 * tp / (2 * tp + fp + fn) if tp else 0.0

    ba = balanced_accuracy([(r["gold"], r["pred"]) for r in rows])
    return {
        "n_items": n,
        "n_criteria": len({r["criterion_id"] for r in rows}),
        "n_trials": len({r["trial"] for r in rows}),
        "n_errors": n - k,
        "accuracy": round(k / n, 4) if n else None,
        "wilson_95": (round(lo, 4), round(hi, 4)),
        "macro_f1": round((f1(True) + f1(False)) / 2, 4) if n else None,
        "balanced_accuracy": None if ba is None else round(ba, 4),
        "gold_met_rate": round(sum(r["gold"] for r in rows) / n, 4) if n else None,
        "model_met_rate": round(sum(r["pred"] for r in rows) / n, 4) if n else None,
        "ece": round(expected_calibration_error([(r["confidence"], r["correct"]) for r in rows]), 4) if n else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Re-score Arm 1 on the verified subset.")
    ap.add_argument("--verdicts", default="annotation/arm1_verification.csv")
    ap.add_argument("--predictions", default="results/real_criteria__openai.json")
    ap.add_argument("--annotator1", default="annotation/annotator1_labels.csv")
    ap.add_argument("--annotator2", default="annotation/annotator2_labels.csv")
    ap.add_argument("--seed", type=int, default=29, help="Seed of the released run.")
    ap.add_argument("--out", default="results/real_criteria_verified")
    args = ap.parse_args()

    verdicts = load_verdicts(args.verdicts)
    forms = harmonized_real_criteria(max_per_study=4, limit=None)
    missing = [f.criterion_id for f in forms if f.criterion_id not in verdicts]
    if missing:
        raise SystemExit(f"{len(missing)} criteria have no verdict, e.g. {missing[0]}")
    items = generate_real_criteria_items(forms, n_per_criterion=2, seed=args.seed)
    result = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    preds = {p["item_id"]: p for p in result["per_item_predictions"]}

    rows = []
    for it in items:
        p = preds.get(it.item_id)
        if p is None:
            raise SystemExit(f"No released prediction for {it.item_id}")
        if (p["gold"] == "met") != it.gold:
            raise SystemExit(f"Gold label for {it.item_id} does not reproduce; wrong seed?")
        rows.append({
            "item_id": it.item_id, "criterion_id": it.criterion.criterion_id, "trial": it.group,
            "gold": it.gold, "pred": p["predicted"] == "met", "correct": bool(p["correct"]),
            "confidence": float(p["confidence"]),
            "verdict": verdicts[it.criterion.criterion_id],
            "currency_ambiguous": currency_ambiguous_leaves(it.criterion.expression, it.facts) > 0,
        })

    subsets = {
        "all_items": rows,
        "verified_criteria": [r for r in rows if r["verdict"] == "keep"],
        "verified_no_currency_convention": [r for r in rows
                                            if r["verdict"] == "keep" and not r["currency_ambiguous"]],
    }
    report = {name: summarise(rs) for name, rs in subsets.items()}
    report["n_criteria_dropped"] = sum(1 for v in verdicts.values() if v == "drop")
    report["n_criteria_total"] = len(verdicts)

    # Agreement, with Arm 1 errors outside the headline subset removed.
    a, b = load_annotations(args.annotator1), load_annotations(args.annotator2)
    kept_ids = {r["item_id"] for r in subsets["verified_no_currency_convention"]}

    def keep(item_id: str, info: dict) -> bool:
        return info["arm"] != "real_criteria" or item_id in kept_ids

    a_f = {i: v for i, v in a.items() if keep(i, v)}
    b_f = {i: v for i, v in b.items() if keep(i, v)}
    full, filt = agreement_report(a, b), agreement_report(a_f, b_f)

    def brief(rep: dict) -> dict:
        return {"n": rep["n_shared_items"], "overall": {k: rep["overall"][k] for k in ("kappa", "ci_95", "percent_agreement")},
                "by_arm": {arm: {"n": blk["n"], "kappa": blk["kappa"], "ci_95": blk["ci_95"]}
                           for arm, blk in rep["by_arm"].items()}}

    report["agreement_all_errors"] = brief(full)
    report["agreement_verified_errors"] = brief(filt)

    stem = Path(args.out)
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8", newline="\n")
    md = to_markdown(report)
    stem.with_suffix(".md").write_text(md, encoding="utf-8", newline="\n")
    print(md)
    print(f"[wrote] {stem.with_suffix('.json')}  {stem.with_suffix('.md')}")


def to_markdown(rep: dict) -> str:
    label = {
        "all_items": "All items (released figure)",
        "verified_criteria": "Verified criteria",
        "verified_no_currency_convention": "Verified criteria, no currency-convention items (headline)",
    }
    out = ["# Arm 1 re-scored on the verified subset", "",
           "Generated by `scripts/rescore_real_criteria.py` from the released predictions; no model calls.",
           f"Criteria kept: {rep['n_criteria_total'] - rep['n_criteria_dropped']} of {rep['n_criteria_total']}.", "",
           "| Subset | Items | Criteria | Trials | Errors | Accuracy [95% CI] | Macro-F1 | Balanced acc. | Gold met | Model met | ECE |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key in ("all_items", "verified_criteria", "verified_no_currency_convention"):
        s = rep[key]
        out.append(f"| {label[key]} | {s['n_items']} | {s['n_criteria']} | {s['n_trials']} | {s['n_errors']} | "
                   f"{s['accuracy']:.3f} [{s['wilson_95'][0]:.3f}, {s['wilson_95'][1]:.3f}] | {s['macro_f1']:.3f} | "
                   f"{s['balanced_accuracy']:.3f} | {s['gold_met_rate']:.3f} | {s['model_met_rate']:.3f} | {s['ece']:.3f} |")
    out += ["", "## Inter-annotator agreement", "",
            "| Error set | n | Cohen's kappa [95% CI] | Real criteria (n, kappa) | Compositional (n, kappa) |",
            "|---|---|---|---|---|"]
    for key, name in (("agreement_all_errors", "All 179 errors (released)"),
                      ("agreement_verified_errors", "Arm 1 errors outside the headline subset removed")):
        g = rep[key]
        o = g["overall"]
        arms = g["by_arm"]

        def cell(arm: str) -> str:
            blk = arms.get(arm)
            if not blk or blk["kappa"] is None:
                return "-"
            return f"{blk['n']}, {blk['kappa']:.3f}"

        out.append(f"| {name} | {g['n']} | {o['kappa']:.3f} [{o['ci_95'][0]:.3f}, {o['ci_95'][1]:.3f}] | "
                   f"{cell('real_criteria')} | {cell('compositional')} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main()
