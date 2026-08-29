"""Command-line entrypoint for CriteriaLogic.
Exposed as the ``criterialogic-eval`` console script (see pyproject) and reused by
``scripts/run_eval.py``. Living inside the installed package is what makes the
console command importable after ``pip install`` (a bare ``scripts/`` directory is
not installed, so an entry point pointing at it fails).
Zero-argument demo (runs end-to-end with NO external data):
    criterialogic-eval
    # or, equivalently, from a clone:  python scripts/run_eval.py
Targeted run:
    criterialogic-eval --task matching --model rule_based
    criterialogic-eval --task compositional --model negation_blind
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.eval.report import render_report
from criterialogic.eval.runner import run_task
from criterialogic.models import OFFLINE_MODELS, REGISTRY
from criterialogic.tasks.compositional import generate_compositional_items


def build_items(task: str):
    if task == "matching":
        return generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=8, seed=13)
    if task == "compositional":
        return generate_compositional_items(n_per_depth=12, max_depth=3, seed=29)
    raise SystemExit(f"Unknown/unsupported demo task: {task}")
def main() -> None:
    ap = argparse.ArgumentParser(description="Run a CriteriaLogic evaluation.")
    ap.add_argument("--task", choices=["matching", "compositional"], default=None)
    ap.add_argument("--model", choices=sorted(REGISTRY), default=None)
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()
    tasks = [args.task] if args.task else ["matching", "compositional"]
    models = [args.model] if args.model else OFFLINE_MODELS
    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    results = []
    for task in tasks:
        items = build_items(task)
        for mname in models:
            model = REGISTRY[mname]()
            res = run_task(model, items, seed=13)
            results.append(res)
            out = Path(args.outdir) / f"{task}__{mname}.json"
            out.write_text(json.dumps(res, indent=2))
            print(f"[wrote] {out}")
    report = render_report(results)
    (Path(args.outdir) / "report.md").write_text(report)
    print("\n" + report)
if __name__ == "__main__":
    main()
