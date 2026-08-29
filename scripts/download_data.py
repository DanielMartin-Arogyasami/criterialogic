#!/usr/bin/env python3
"""Pull the data CriteriaLogic needs.
Releasable sources are fetched; the DUA-gated one is only located, never downloaded.
    python scripts/download_data.py --all                 # Chia + a default ctgov cache, + n2c2 status
    python scripts/download_data.py --chia                 # download + extract Chia (brat .txt/.ann) from figshare
    python scripts/download_data.py --chia --hf            # alternative Chia route via Hugging Face (needs `datasets`)
    python scripts/download_data.py --ctgov "type 2 diabetes" --n 100   # cache ClinicalTrials.gov eligibility text
    python scripts/download_data.py --status               # show what is present locally (incl. n2c2 DUA status)
n2c2 2018 is DUA-gated: this tool never downloads it. Obtain it from the Harvard DBMI
portal and place the patient XML under data/raw/n2c2_2018/ (gitignored).
"""
from __future__ import annotations

import argparse
import json
import sys

from criterialogic.data import download as dl


def main() -> None:
    ap = argparse.ArgumentParser(description="Pull CriteriaLogic data (releasable sources only).")
    ap.add_argument("--all", action="store_true", help="Chia + default ctgov cache + n2c2 status.")
    ap.add_argument("--chia", action="store_true", help="Download + extract Chia (CC-BY) from figshare.")
    ap.add_argument("--hf", action="store_true", help="Use the Hugging Face Chia route (needs `datasets`).")
    ap.add_argument("--force", action="store_true", help="Re-download Chia even if already present.")
    ap.add_argument("--ctgov", metavar="QUERY", nargs="?", const="type 2 diabetes",
                    help="Cache ClinicalTrials.gov eligibility text for QUERY.")
    ap.add_argument("--n", type=int, default=50, help="Number of trials for --ctgov (default 50).")
    ap.add_argument("--status", action="store_true", help="Report what is present locally; downloads nothing.")
    args = ap.parse_args()
    if not any([args.all, args.chia, args.ctgov is not None, args.status]):
        ap.print_help()
        return
    def show(d: dict) -> None:
        print(json.dumps(d, indent=2))
    try:
        if args.status:
            show(dl.verify())
            return
        if args.chia or args.all:
            if args.hf:
                show(dl.download_chia_hf())
            else:
                show(dl.download_chia_figshare(force=args.force))
        if args.ctgov is not None or args.all:
            query = args.ctgov if args.ctgov is not None else "type 2 diabetes"
            show(dl.cache_ctgov_criteria(query=query, n=args.n))
        if args.all:
            print("\nn2c2 2018 (DUA-gated — not downloaded):")
            show(dl.n2c2_status())
    except dl.DownloadError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
if __name__ == "__main__":
    main()
