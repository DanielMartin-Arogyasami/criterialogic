#!/usr/bin/env python3
"""Generate the compositional stress test deterministically and save it.

    python scripts/build_logic_set.py --depths 2,3,4,5,6 --n-per-depth 60 --seed 29
    python scripts/build_logic_set.py --max-depth 4 --n-per-depth 100 --seed 29

Same seed + same depth list + same atom pool -> byte-identical set. The pool digest is
stamped on every item, so a set built against a different pool is distinguishable rather
than silently mixed.

Note on the reported depth sweep: it predates the --depths argument and was built by
generating 1..d and keeping the depth-d slice. Use
``criterialogic.tasks.compositional.regenerate_reported_depth_set`` to reproduce those
exact sets; use --depths for new work, because it varies only depth.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.tasks.compositional import generate_compositional_items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-depth", type=int, default=60)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--depths", default=None, help="Comma-separated, e.g. 2,3,4,5,6.")
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--out", default="data/processed/logic_set.json")
    args = ap.parse_args()

    depths = [int(d) for d in args.depths.split(",")] if args.depths else None
    items = generate_compositional_items(n_per_depth=args.n_per_depth,
                                         max_depth=args.max_depth,
                                         seed=args.seed, depths=depths)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps([it.model_dump(mode="json") for it in items],
                                         indent=2))
    ladder = depths or list(range(1, args.max_depth + 1))
    met = sum(1 for it in items if it.gold)
    print(f"[wrote] {args.out}  ({len(items)} items, depths {ladder}, seed={args.seed})")
    print(f"  gold met-rate: {met / len(items):.4f}")
    print(f"  atom pool sha256: {items[0].criterion.metadata.get('atom_pool_sha256', '?')[:16]}...")


if __name__ == "__main__":
    main()
