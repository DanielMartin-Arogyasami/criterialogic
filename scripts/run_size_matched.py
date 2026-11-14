#!/usr/bin/env python3
"""Build and run the size-matched compositional set (depth varies; size does not).

    python scripts/run_size_matched.py                  # offline check, no key needed
    python scripts/run_size_matched.py --model openai   # the real run: gpt-4o-mini, prompt v2

The offline check builds the set, runs the two diagnostic models (the oracle, which
must score 1.0, and the deliberately broken negation-blind model), and prints the
per-depth structure table, so you can confirm that leaves, groups, NOT nodes and the
gold base rate are flat across depth before spending anything.

The real run needs OPENAI_API_KEY (or a .env file, as for the released runs). It uses
gpt-4o-mini at temperature 0 with prompt v2 — the configuration of the released runs —
unless --llm-model says otherwise. 500 items at the defaults.

Writes:
    data/processed/logic_set_size_matched.json   the item set (deterministic)
    results/size_matched/compositional__<model>.json   per-item predictions and metrics
    results/size_matched/report__<model>.md            the usual evaluation report
    results/size_matched/structure__<model>.{json,md}  per-depth structure + item-level trend
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.eval.report import render_report
from criterialogic.eval.runner import run_task
from criterialogic.eval.structure_report import analyse, to_markdown
from criterialogic.models import LLM_MODELS, OFFLINE_MODELS, REGISTRY
from criterialogic.tasks.size_matched import (
    DEFAULT_GROUPS,
    DEFAULT_LEAVES,
    DEFAULT_NOTS,
    generate_size_matched_items,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build and run the size-matched compositional set.")
    ap.add_argument("--model", choices=sorted(REGISTRY), default=None,
                    help="Default: the offline diagnostic models (no key).")
    ap.add_argument("--llm-model", default="gpt-4o-mini",
                    help="Model name for an LLM adapter. Default matches the released runs.")
    ap.add_argument("--depths", default="2,3,4,5,6")
    ap.add_argument("--n-per-depth", type=int, default=100)
    ap.add_argument("--leaves", type=int, default=DEFAULT_LEAVES)
    ap.add_argument("--groups", type=int, default=DEFAULT_GROUPS)
    ap.add_argument("--nots", type=int, default=DEFAULT_NOTS)
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--items-out", default="data/processed/logic_set_size_matched.json")
    ap.add_argument("--outdir", default="results/size_matched")
    ap.add_argument("--n-permutations", type=int, default=20000)
    args = ap.parse_args()

    depths = [int(d) for d in args.depths.split(",")]
    items = generate_size_matched_items(depths=depths, n_per_depth=args.n_per_depth,
                                        seed=args.seed, n_leaves=args.leaves,
                                        n_groups=args.groups, n_nots=args.nots)
    items_path = Path(args.items_out)
    items_path.parent.mkdir(parents=True, exist_ok=True)
    items_path.write_text(json.dumps([it.model_dump(mode="json") for it in items], indent=2), encoding="utf-8", newline="\n")
    print(f"[wrote] {items_path}  ({len(items)} items, depths {depths}, "
          f"{args.leaves} leaves, {args.groups} groups, {args.nots} NOTs, seed={args.seed})")

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
        s = analyse(f"Size-matched set: {name}", str(items_path), str(out), args.n_permutations)
        sets.append(s)
        (outdir / f"structure__{name}.json").write_text(json.dumps(s, indent=2), encoding="utf-8", newline="\n")
        (outdir / f"structure__{name}.md").write_text(to_markdown([s]), encoding="utf-8", newline="\n")
        print(f"[wrote] {out}, report__{name}.md, structure__{name}.json/.md")

    print("\n" + to_markdown(sets))


if __name__ == "__main__":
    main()
