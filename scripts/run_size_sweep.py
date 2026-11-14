#!/usr/bin/env python3
"""Build and run the fixed-depth size sweep (size varies; depth does not).

    python scripts/run_size_sweep.py                  # offline check, no key needed
    python scripts/run_size_sweep.py --model openai   # the real run: gpt-4o-mini, prompt v2

The converse of scripts/run_size_matched.py. Depth is held at 3 while the number of
leaves doubles from 7 to 112; groups and NOT nodes grow in the size-matched set's ratio
(6 groups and 4 NOTs per 14 leaves), so the 14-leaf level is the size-matched set's
depth-3 configuration drawn again. The gold label is half met at every size.

The offline check runs the oracle (must score 1.0) and the negation-blind diagnostic and
prints the per-size structure table, so you can confirm depth stays at 3 and only size
changes before spending anything. The real run needs OPENAI_API_KEY (or a .env file).
500 items at the defaults; the largest prompts are about 9,000 characters.

Writes:
    data/processed/logic_set_size_sweep.json          the item set (deterministic)
    results/size_sweep/compositional__<model>.json    per-item predictions and metrics
    results/size_sweep/report__<model>.md             the usual evaluation report
    results/size_sweep/structure__<model>.{json,md}   per-size structure + item-level trend
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.eval.report import render_report
from criterialogic.eval.runner import run_task
from criterialogic.eval.structure_report import analyse_by_size, to_markdown_by_size
from criterialogic.models import LLM_MODELS, OFFLINE_MODELS, REGISTRY
from criterialogic.tasks.size_matched import (
    DEFAULT_SWEEP_DEPTH,
    DEFAULT_SWEEP_SIZES,
    generate_size_sweep_items,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build and run the fixed-depth size sweep.")
    ap.add_argument("--model", choices=sorted(REGISTRY), default=None,
                    help="Default: the offline diagnostic models (no key).")
    ap.add_argument("--llm-model", default="gpt-4o-mini",
                    help="Model name for an LLM adapter. Default matches the released runs.")
    ap.add_argument("--depth", type=int, default=DEFAULT_SWEEP_DEPTH)
    ap.add_argument("--n-per-size", type=int, default=100)
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--items-out", default="data/processed/logic_set_size_sweep.json")
    ap.add_argument("--outdir", default="results/size_sweep")
    ap.add_argument("--n-permutations", type=int, default=20000)
    args = ap.parse_args()

    items = generate_size_sweep_items(sizes=DEFAULT_SWEEP_SIZES, depth=args.depth,
                                      n_per_size=args.n_per_size, seed=args.seed)
    items_path = Path(args.items_out)
    items_path.parent.mkdir(parents=True, exist_ok=True)
    items_path.write_text(json.dumps([it.model_dump(mode="json") for it in items], indent=2),
                          encoding="utf-8", newline="\n")
    sizes = ", ".join(f"{a} leaves/{b} groups/{c} NOTs" for a, b, c in DEFAULT_SWEEP_SIZES)
    print(f"[wrote] {items_path}  ({len(items)} items, depth {args.depth}, sizes: {sizes}, seed={args.seed})")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    names = [args.model] if args.model else OFFLINE_MODELS
    sets = []
    for name in names:
        kwargs = {"model": args.llm_model, "prompt_version": "2"} if name in LLM_MODELS else {}
        model = REGISTRY[name](**kwargs)
        res = run_task(model, items, seed=args.seed)
        out = outdir / f"compositional__{name}.json"
        out.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8", newline="\n")
        (outdir / f"report__{name}.md").write_text(render_report([res]), encoding="utf-8", newline="\n")
        s = analyse_by_size(f"Fixed-depth size sweep: {name}", str(items_path), str(out), args.n_permutations)
        sets.append(s)
        (outdir / f"structure__{name}.json").write_text(json.dumps(s, indent=2), encoding="utf-8", newline="\n")
        (outdir / f"structure__{name}.md").write_text(to_markdown_by_size([s]), encoding="utf-8", newline="\n")
        print(f"[wrote] {out}, report__{name}.md, structure__{name}.json/.md")

    print("\n" + to_markdown_by_size(sets))


if __name__ == "__main__":
    main()
