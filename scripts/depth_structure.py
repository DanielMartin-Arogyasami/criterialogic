#!/usr/bin/env python3
"""Per-depth structure and item-level trend for compositional item sets.

    python scripts/depth_structure.py
    python scripts/depth_structure.py --set "Size-matched" data/processed/logic_set_size_matched.json results/size_matched/compositional__openai.json

For each depth this reports what else the depth level carries: leaves, AND / OR / NOT
counts, depth after canonicalisation, undocumented leaves, leaves whose label rests on
the currency convention, prompt length, the gold met-rate and the model's met-rate,
accuracy with a Wilson interval, and balanced accuracy. For each set it adds the
item-level trend (stats.item_level_trend) and the item-level correlation between depth
and log2(leaves), which says how far depth and size can be told apart in that set.

Deterministic, no network, no key: it reads released item sets and released
per-item predictions only. Writes results/depth_structure.{json,md} by default.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.eval.structure_report import analyse, to_markdown

DEFAULT_SETS = [
    ("Depth sweep (depths 2-6, 60 per depth)", "data/processed/logic_set_depth_sweep.json",
     "results/compositional__openai.json"),
    ("Mixed set (depths 1-4, 100 per depth)", "data/processed/logic_set_mixed.json",
     "results/mixed_v2/compositional__openai.json"),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--set", nargs=3, action="append", metavar=("NAME", "ITEMS", "PREDICTIONS"),
                    help="Add an item set and its result file. Default: the two released sets.")
    ap.add_argument("--n-permutations", type=int, default=20000)
    ap.add_argument("--out", default="results/depth_structure",
                    help="Output path stem; .json and .md are written.")
    args = ap.parse_args()
    specs = args.set or DEFAULT_SETS
    sets = [analyse(name, items, preds, args.n_permutations) for name, items, preds in specs]
    stem = Path(args.out)
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".json").write_text(json.dumps({"generated_by": "scripts/depth_structure.py", "sets": sets}, indent=2), encoding="utf-8", newline="\n")
    md = to_markdown(sets)
    stem.with_suffix(".md").write_text(md, encoding="utf-8", newline="\n")
    print(md)
    print(f"[wrote] {stem.with_suffix('.json')}  {stem.with_suffix('.md')}")


if __name__ == "__main__":
    main()
