#!/usr/bin/env python3
"""Draw the annotation sample and write the two blind annotator files.

    python scripts/annotation_export.py --results results/ \
        --depths 2,3,4,5,6 --n-per-depth 60 --n 200 --out annotation/

The generation arguments are not optional. Item sets are regenerated here rather than
read back from the result files, so omitting them rebuilds a different set: the depth
sweep comes back as 180 items instead of 300 and the sample is drawn from whichever
subset happens to match.

Reads the result files written by the evaluation runner, pools their errors, draws a
sample stratified across models and nesting depths, and writes:

    annotation/errors_annotator1.csv        blind: no automatic label
    annotation/errors_annotator2.csv        blind: no automatic label, no other annotator
    annotation/automatic_labels_HELD_BACK.csv   for the third-signal comparison later

Both annotators work from docs/CODEBOOK.md, independently, filling `category` and
ticking `clinical_judgement_required` whenever the decision depends on medical
knowledge. Run the twenty-item calibration session first and discard those items — they
do not enter the reliability statistics.

Item sets are regenerated here rather than stored in the result files, so this must be
called with the same generation arguments the evaluation used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.cli import build_items
from criterialogic.tasks.base import Prediction
from criterialogic.taxonomy.reliability import (
    MINIMUM_SAMPLE,
    export_for_annotation,
    sample_error_set,
)

#: Neither is a system under test. `rule_based` is the oracle and produces no errors;
#: `negation_blind` is deliberately broken and its errors all share one templated
#: rationale, so labelling them is trivially consistent and inflates kappa.
DIAGNOSTIC_MODELS = ("rule_based", "negation_blind")


def _load_runs(results_dir: Path, args) -> dict:
    """Rebuild {label: (items, predictions)} from result files."""
    runs: dict = {}
    for path in sorted(results_dir.glob("*.json")):
        data = json.loads(path.read_text())
        if "per_item_predictions" not in data or "task" not in data:
            continue
        task = data["task"]
        if task not in ("real_criteria", "compositional"):
            continue
        items = build_items(task, args)
        by_id = {it.item_id: it for it in items}
        preds, kept = [], []
        for row in data["per_item_predictions"]:
            if row["item_id"] not in by_id:
                continue
            kept.append(by_id[row["item_id"]])
            preds.append(Prediction(item_id=row["item_id"],
                                    label=row["predicted"] == "met",
                                    confidence=row.get("confidence", 0.5),
                                    abstain=row.get("abstain", False),
                                    rationale=row.get("rationale")))
        if not kept:
            print(f"[skip] {path.name}: no item ids matched the regenerated set — "
                  f"pass the same generation arguments the run used.")
            continue
        name = data["model"].get("name", path.stem)
        if args.models:
            if name not in args.models:
                print(f"[skip] {path.name}: {name} not in --models")
                continue
        elif not args.include_diagnostics and name in DIAGNOSTIC_MODELS:
            print(f"[skip] {path.name}: {name} is a diagnostic, not a system under test")
            continue

        # A partial match is the dangerous case. No match already prints and skips, but
        # matching 180 of 300 looks like success and silently annotates the wrong sample.
        n_run = len(data["per_item_predictions"])
        if len(kept) != n_run:
            raise SystemExit(
                f"{path.name}: regenerated set matched {len(kept)} of {n_run} items.\n"
                f"Pass the generation arguments the run used. For the depth sweep:\n"
                f"  --depths 2,3,4,5,6 --n-per-depth 60")

        label = f"{task}::{name}"
        runs[label] = (kept, preds)
        print(f"[loaded] {path.name} -> {label} ({len(kept)} items)")
    return runs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="annotation")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--sample-seed", type=int, default=11)
    ap.add_argument("--prompt-version", default="2",
                    help="Renderer version the evaluated run used. Pass 1 when annotating "
                         "the v0.2 reported results, so annotators see the prompt the "
                         "model actually saw.")
    ap.add_argument("--models", default=None,
                    help="Comma-separated allowlist of model names. Overrides the "
                         "diagnostic exclusion.")
    ap.add_argument("--include-diagnostics", action="store_true",
                    help="Include rule_based and negation_blind. Off by default: they "
                         "are diagnostics, and negation_blind's errors share one "
                         "templated rationale.")
    ap.add_argument("--include-unanswerable", action="store_true",
                    help="Include items whose gold label rests on an unstated fact. Off "
                         "by default: those are renderer defects, not reasoning failures.")
    ap.add_argument("--n-per-depth", type=int, default=60)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--depths", default=None)
    ap.add_argument("--n-per-criterion", type=int, default=2)
    ap.add_argument("--max-per-study", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    args.models = [m.strip() for m in args.models.split(",")] if args.models else None

    runs = _load_runs(Path(args.results), args)
    if not runs:
        raise SystemExit(f"No usable result files in {args.results}/.")

    sample = sample_error_set(runs, n=args.n, seed=args.sample_seed,
                              include_unanswerable=args.include_unanswerable,
                              prompt_version=args.prompt_version)
    if not sample:
        raise SystemExit("No errors to annotate.")
    info = export_for_annotation(sample, args.out)
    print(json.dumps(info, indent=2))
    if not info["meets_minimum"]:
        print(f"\nWARNING: {info['n_items']} items is below the {MINIMUM_SAMPLE}-item "
              f"floor. The kappa interval will be wide; report the n prominently or "
              f"widen the error pool by running more models or depths.")


if __name__ == "__main__":
    main()
