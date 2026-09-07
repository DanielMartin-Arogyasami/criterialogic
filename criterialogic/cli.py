"""Command-line entrypoint.

Exposed as the ``criterialogic-eval`` console script and reused by
``scripts/run_eval.py``. Living inside the installed package is what makes the console
command importable after ``pip install``.

    criterialogic-eval                                     # offline diagnostics, both arms
    criterialogic-eval --task compositional --depths 2,3,4,5,6 --n-per-depth 60
    criterialogic-eval --task real_criteria --model openai

Both arms need the ClinicalTrials.gov snapshot in ``data/`` (committed), and nothing
else. No API key is needed for the offline models.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.data.harmonize import harmonized_real_criteria
from criterialogic.env import load_dotenv  # noqa: F401
from criterialogic.eval.report import render_report
from criterialogic.eval.runner import run_task
from criterialogic.models import LLM_MODELS, OFFLINE_MODELS, REGISTRY
from criterialogic.tasks.compositional import generate_compositional_items
from criterialogic.tasks.real_criteria import generate_real_criteria_items

TASKS = ("real_criteria", "compositional")


def build_items(task: str, args):
    if task == "real_criteria":
        forms = harmonized_real_criteria(max_per_study=args.max_per_study,
                                         limit=args.limit)
        if not forms:
            raise SystemExit(
                "No criteria were segmented. The ClinicalTrials.gov cache is either "
                "missing or the extraction rules matched nothing — check "
                "data/ctgov_cache/ and run scripts/build_real_criteria.py --stats."
            )
        return generate_real_criteria_items(forms, n_per_criterion=args.n_per_criterion,
                                            seed=args.seed)
    if task == "compositional":
        depths = [int(d) for d in args.depths.split(",")] if args.depths else None
        return generate_compositional_items(n_per_depth=args.n_per_depth,
                                            max_depth=args.max_depth,
                                            seed=args.seed, depths=depths)
    raise SystemExit(f"Unknown task: {task}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a CriteriaLogic evaluation.")
    ap.add_argument("--task", choices=TASKS, default=None,
                    help="Default: run both arms.")
    ap.add_argument("--model", choices=sorted(REGISTRY), default=None,
                    help="Default: the offline diagnostic models.")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--seed", type=int, default=29)
    # compositional
    ap.add_argument("--n-per-depth", type=int, default=60)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--depths", default=None,
                    help="Comma-separated depth list, e.g. 2,3,4,5,6. Overrides --max-depth.")
    # real criteria
    ap.add_argument("--n-per-criterion", type=int, default=2)
    ap.add_argument("--max-per-study", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None,
                    help="Cap the number of criteria (smoke tests).")
    ap.add_argument("--prompt-version", default=None,
                    help="LLM prompt renderer version. Use 1 to reproduce the v0.2 "
                         "reported numbers exactly; 2 (default) fixes the currency "
                         "rendering defect. See results/SECTION7.md.")
    args = ap.parse_args()

    tasks = [args.task] if args.task else list(TASKS)
    models = [args.model] if args.model else OFFLINE_MODELS
    Path(args.outdir).mkdir(parents=True, exist_ok=True)

    results = []
    for task in tasks:
        items = build_items(task, args)
        for name in models:
            kwargs = {}
            if name in LLM_MODELS and args.prompt_version:
                kwargs["prompt_version"] = args.prompt_version
            model = REGISTRY[name](**kwargs)
            res = run_task(model, items, seed=args.seed)
            results.append(res)
            out = Path(args.outdir) / f"{task}__{name}.json"
            out.write_text(json.dumps(res, indent=2, default=str))
            print(f"[wrote] {out}")

    report = render_report(results)
    (Path(args.outdir) / "report.md").write_text(report)
    print("\n" + report)


if __name__ == "__main__":
    main()
