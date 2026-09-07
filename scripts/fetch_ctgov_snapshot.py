#!/usr/bin/env python3
"""Freeze a dated ClinicalTrials.gov snapshot and build the atom pool from it.

    python scripts/fetch_ctgov_snapshot.py --limit 300 --first-posted-from 2026-01-01
    python scripts/fetch_ctgov_snapshot.py --recruiting --limit 300 --first-posted-from 2026-06-01
    python scripts/fetch_ctgov_snapshot.py --offline          # rebuild the pool, no network

Both benchmark arms come from this one snapshot: the criteria (Arm 1, via
scripts/build_real_criteria.py) and the atom pool the compositional stress test composes
over (Arm 2). The raw records land in data/ctgov_cache/ one JSON per NCT ID, alongside a
MANIFEST.json recording the exact query, the frame field by field, and a snapshot id.

`--first-posted-from` is the contamination control: restricting to trials first posted
after an evaluated model's training cutoff turns "probably unseen" into evidence.

WARNING — a rebuild invalidates published numbers. The atom pool's SHA-256 is stamped on
every generated item, so a new pool means new items and every reported result must be
regenerated. The committed snapshot backs the v0.2 results; see results/SECTION7.md
before replacing it.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from criterialogic.data.atom_pool import DEFAULT_POOL_PATH, write_pool
from criterialogic.data.loaders.ctgov import (
    DEFAULT_CACHE,
    StudyQuery,
    build_atom_records,
    fetch_studies,
    load_cached_studies,
    read_manifest,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300,
                    help="Target number of cached studies (default 300).")
    ap.add_argument("--first-posted-from", default=None, metavar="YYYY-MM-DD",
                    help="Only trials first posted on or after this date.")
    ap.add_argument("--recruiting", action="store_true",
                    help="Restrict the frame to AREA[OverallStatus]RECRUITING.")
    ap.add_argument("--status", default=None,
                    help="Explicit overall status, e.g. RECRUITING. Overrides --recruiting.")
    ap.add_argument("--condition", default=None,
                    help="Condition term for a disease-scoped frame. Omit for a "
                         "method-scoped draw, which is what the paper describes.")
    ap.add_argument("--phase", default="PHASE4")
    ap.add_argument("--study-type", default="INTERVENTIONAL")
    ap.add_argument("--max-per-study", type=int, default=None,
                    help="Cap atoms taken from any one trial, to avoid over-weighting it.")
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    ap.add_argument("--out", default=str(DEFAULT_POOL_PATH))
    ap.add_argument("--offline", action="store_true",
                    help="Rebuild the pool from the existing cache; make no requests.")
    args = ap.parse_args()

    status = args.status or ("RECRUITING" if args.recruiting else None)
    query = StudyQuery(phase=args.phase, study_type=args.study_type,
                       first_posted_from=args.first_posted_from,
                       overall_status=status, condition=args.condition)

    if args.offline:
        summary = {"cached_total": len(load_cached_studies(args.cache_dir)), "newly_fetched": 0}
        print(f"[offline] rebuilding from {summary['cached_total']} cached studies")
    else:
        print(f"[frame] {query.advanced_expression()}"
              + (f"  query.cond={args.condition}" if args.condition else ""))
        summary = fetch_studies(query, limit=args.limit, cache_dir=args.cache_dir)
        print(f"[cache] {summary['cached_total']} studies "
              f"({summary['newly_fetched']} newly fetched) in {args.cache_dir}")

    studies = load_cached_studies(args.cache_dir)
    if not studies:
        raise SystemExit(f"No cached studies under {args.cache_dir}. Run without --offline.")

    manifest = read_manifest(args.cache_dir) or {}
    fetched_utc = manifest.get("fetched_utc") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    records, stats = build_atom_records(studies, fetched_utc, max_per_study=args.max_per_study)
    if not records:
        raise SystemExit(
            "Extraction produced no atoms. Inspect the cached eligibility text before "
            "loosening the extraction rules — an empty pool is a real result, not a bug "
            "to paper over."
        )

    out = write_pool(records, stats, query_manifest=manifest, path=args.out)
    dated = [r.first_posted for r in records if r.first_posted]
    print(f"[wrote] {out}")
    print(f"  snapshot: {manifest.get('snapshot_id', 'unknown')}")
    print(f"  atoms: {len(records)} from {len({r.nct_id for r in records})} trials")
    print(f"  extraction: {json.dumps(stats.to_json())}")
    print(f"  first-posted range: {min(dated, default=None)} .. {max(dated, default=None)} "
          f"({len(dated)}/{len(records)} atoms dated)")


if __name__ == "__main__":
    main()
