#!/usr/bin/env python3
"""Segment the snapshot's criteria into LogicalForms (Arm 1) and report the yield.

    python scripts/build_real_criteria.py --stats            # counts only, writes nothing
    python scripts/build_real_criteria.py --out data/real_criteria.json

Needs no network and no API key: it reads the committed ClinicalTrials.gov cache. The
numbers it prints are the ones Section 3 of the manuscript reports — criteria mapped,
mapping rate, polarity split, depth histogram — so run it before filling that section
rather than estimating.

Precision over recall by design: a sentence the extractor cannot map faithfully is
skipped and counted, never coerced. A mislabelled gold item is scored as a model failure,
which is worse than a smaller n.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.data.loaders.ctgov import DEFAULT_CACHE, read_manifest
from criterialogic.data.real_criteria import (
    build_criterion_forms,
    polarity_distribution,
    structure_distribution,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    ap.add_argument("--max-per-study", type=int, default=4,
                    help="Cap criteria taken from any one trial (default 4).")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None, help="Write the forms as JSON.")
    ap.add_argument("--stats", action="store_true", help="Print counts and exit.")
    args = ap.parse_args()

    forms, stats = build_criterion_forms(cache_dir=args.cache_dir,
                                         max_per_study=args.max_per_study,
                                         limit=args.limit)
    manifest = read_manifest(args.cache_dir) or {}
    summary = {
        "snapshot_id": manifest.get("snapshot_id", "unknown"),
        "frame": manifest.get("frame", {}),
        "fetched_utc": manifest.get("fetched_utc"),
        "n_criteria": len(forms),
        "n_trials": len({f.metadata.get("trial_id") for f in forms}),
        "segmentation": stats.to_json(),
        "polarity": polarity_distribution(forms),
        "depth_histogram": structure_distribution(forms),
        "first_posted_range": [
            min((f.metadata.get("first_posted", "") for f in forms if f.metadata.get("first_posted")),
                default=None),
            max((f.metadata.get("first_posted", "") for f in forms if f.metadata.get("first_posted")),
                default=None),
        ],
    }
    print(json.dumps(summary, indent=2))
    if args.stats or not args.out:
        return
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(
        {"summary": summary, "criteria": [f.model_dump(mode="json") for f in forms]},
        indent=2), encoding="utf-8")
    print(f"[wrote] {args.out}")


if __name__ == "__main__":
    main()
