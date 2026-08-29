#!/usr/bin/env python3
"""Generate the Task-D compositional-logic stress-test deterministically and save it.
    python scripts/build_logic_set.py --n-per-depth 20 --max-depth 4 --seed 29 --out data/processed/logic_set.json
Reproducible: same seed -> identical set (spec §11).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.tasks.compositional import generate_compositional_items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-depth", type=int, default=20)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--out", default="data/processed/logic_set.json")
    args = ap.parse_args()
    items = generate_compositional_items(args.n_per_depth, args.max_depth, args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps([it.model_dump() for it in items], indent=2, default=str))
    print(f"[wrote] {args.out}  ({len(items)} items, depths 1..{args.max_depth}, seed={args.seed})")
if __name__ == "__main__":
    main()
