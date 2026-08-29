#!/usr/bin/env python3
"""Populate the ClinicalTrials.gov cache and build the Task-D atom pool.

    python scripts/fetch_ctgov_atoms.py --limit 200 --first-posted-from 2025-07-01

Fetches Phase-IV interventional studies from the public v2 API into data/ctgov_cache/
(one raw JSON per NCT ID, never re-fetched) and writes data/ctgov_atom_pool.json, where
every atom carries its source NCT ID, the verbatim sentence it came from, that trial's
first-posted date, and the fetch timestamp.

`--first-posted-from` is the contamination control: restricting to trials first posted
after a model's training cutoff is what gives §3.5 evidence rather than an assumption.

Rerunning with a populated cache is offline and deterministic: pass --offline to rebuild
the pool from the cache without touching the network.
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
    ap.add_argument("--limit", type=int, default=200,
                    help="Target number of cached studies (default 200).")
    ap.add_argument("--first-posted-from", default=None, metavar="YYYY-MM-DD",
                    help="Only trials first posted on or after this date.")
    ap.add_argument("--phase", default="PHASE4")
    ap.add_argument("--study-type", default="INTERVENTIONAL")
    ap.add_argument("--max-per-study", type=int, default=None,
                    help="Cap atoms taken from any one trial, to avoid over-weighting it.")
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    ap.add_argument("--out", default=str(DEFAULT_POOL_PATH))
    ap.add_argument("--offline", action="store_true",
                    help="Rebuild the pool from the existing cache; make no requests.")
    args = ap.parse_args()

    query = StudyQuery(phase=args.phase, study_type=args.study_type,
                       first_posted_from=args.first_posted_from)

    if args.offline:
        summary = {"cached_total": len(load_cached_studies(args.cache_dir)),
                   "newly_fetched": 0, "cache_dir": args.cache_dir}
        print(f"[offline] rebuilding from {summary['cached_total']} cached studies")
    else:
        summary = fetch_studies(query, limit=args.limit, cache_dir=args.cache_dir)
        print(f"[cache] {summary['cached_total']} studies "
              f"({summary['newly_fetched']} newly fetched) in {summary['cache_dir']}")

    studies = load_cached_studies(args.cache_dir)
    if not studies:
        raise SystemExit(
            f"No cached studies under {args.cache_dir}. Run without --offline to fetch."
        )

    manifest = read_manifest(args.cache_dir) or {}
    fetched_utc = manifest.get("fetched_utc") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    records, stats = build_atom_records(studies, fetched_utc, max_per_study=args.max_per_study)
    if not records:
        raise SystemExit(
            "Extraction produced no atoms. Inspect the cached eligibility text before "
            "loosening the extraction rules — an empty pool is a real result, not a bug to "
            "paper over."
        )

    out = write_pool(records, stats, query_manifest=manifest, path=args.out)
    dated = sum(1 for r in records if r.first_posted)
    earliest = min((r.first_posted for r in records if r.first_posted), default=None)
    latest = max((r.first_posted for r in records if r.first_posted), default=None)
    print(f"[wrote] {out}")
    print(f"  atoms: {len(records)} from {len({r.nct_id for r in records})} trials")
    print(f"  extraction: {json.dumps(stats.to_json())}")
    print(f"  first-posted range: {earliest} .. {latest} ({dated}/{len(records)} atoms dated)")


if __name__ == "__main__":
    main()
