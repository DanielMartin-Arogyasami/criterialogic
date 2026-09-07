#!/usr/bin/env python3
"""Turn a model's predictions into a leaderboard submission file, and score it.

    python scripts/make_submission.py --model openai --task compositional --out sub.json
    python scripts/make_submission.py --score sub.json --task compositional

This is the whole submission path. If writing a wrapper for a new model and getting a
scored submission out of it takes longer than about thirty minutes from a cold start
following only the README, the instructions need work rather than the contributor.
"""
from __future__ import annotations

import argparse
import json

from criterialogic.cli import build_items
from criterialogic.env import load_dotenv  # noqa: F401
from criterialogic.leaderboard.score import score_submission
from criterialogic.leaderboard.submit import load_submission, validate_against_items
from criterialogic.models import LLM_MODELS, REGISTRY


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["real_criteria", "compositional"], required=True)
    ap.add_argument("--model", choices=sorted(REGISTRY), default=None)
    ap.add_argument("--out", default="submission.json")
    ap.add_argument("--score", default=None, metavar="PATH",
                    help="Score an existing submission instead of producing one.")
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--n-per-depth", type=int, default=60)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--depths", default=None)
    ap.add_argument("--n-per-criterion", type=int, default=2)
    ap.add_argument("--max-per-study", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--prompt-version", default=None)
    args = ap.parse_args()

    items = build_items(args.task, args)

    if args.score:
        sub = load_submission(args.score)
        validate_against_items(sub, items)
        result = score_submission(sub, items)
        print(json.dumps({"model": sub["model"], "task": sub["task"],
                          "metrics": result["metrics"],
                          "calibration": result["calibration"],
                          "failure_taxonomy": result["failure_taxonomy"]},
                         indent=2, default=str))
        return

    if not args.model:
        raise SystemExit("--model is required unless --score is given.")
    model = REGISTRY[args.model](
        **({"prompt_version": args.prompt_version} if args.model in LLM_MODELS
           and args.prompt_version else {}))
    predictions = model.predict_batch(items)
    payload = {
        "model": model.info().get("name", args.model),
        "task": args.task,
        "model_info": model.info(),
        "predictions": [{"item_id": p.item_id, "label": p.label,
                         "confidence": p.confidence, "abstain": p.abstain,
                         "rationale": p.rationale} for p in predictions],
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(f"[wrote] {args.out}  ({len(predictions)} predictions)")
    print(f"Validate and score with:  python scripts/make_submission.py "
          f"--score {args.out} --task {args.task}")


if __name__ == "__main__":
    main()
