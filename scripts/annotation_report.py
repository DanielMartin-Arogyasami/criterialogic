#!/usr/bin/env python3
"""Compute inter-annotator agreement, list disagreements, and build the consensus labels.

Three steps, in order:

    # 1. agreement + the adjudication sheet
    python scripts/annotation_report.py --a annotation/errors_annotator1.csv \
                                        --b annotation/errors_annotator2.csv \
                                        --adjudication-out annotation/adjudication.csv

    # 2. (fill resolved_category for every row in adjudication.csv)

    # 3. final report, including the consensus distribution and the third signal
    python scripts/annotation_report.py --a ... --b ... \
        --adjudication annotation/adjudication.csv \
        --automatic annotation/automatic_labels_HELD_BACK.csv \
        --out results/agreement.json

Reports kappa with a bootstrap 95% interval, percent agreement, a per-category
breakdown, and the same three sliced by arm, by depth, and by whether the item was
flagged as needing clinical judgement. Publish whatever it says: a low kappa is a real
finding about how hard error attribution is.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from criterialogic.taxonomy.reliability import (
    agreement_report,
    automatic_vs_consensus,
    consensus_labels,
    disagreements,
    load_adjudication,
    load_annotations,
    write_adjudication_sheet,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="Annotator 1 CSV.")
    ap.add_argument("--b", required=True, help="Annotator 2 CSV.")
    ap.add_argument("--adjudication", default=None, help="Filled adjudication CSV.")
    ap.add_argument("--adjudication-out", default=None,
                    help="Write a blank adjudication sheet for the disagreements.")
    ap.add_argument("--automatic", default=None,
                    help="Held-back automatic labels, for the third-signal comparison.")
    ap.add_argument("--out", default=None, help="Write the report as JSON.")
    ap.add_argument("--bootstrap", type=int, default=5000)
    args = ap.parse_args()

    a, b = load_annotations(args.a), load_annotations(args.b)
    report = agreement_report(a, b, n_boot=args.bootstrap)

    dis = disagreements(a, b)
    report["n_disagreements"] = len(dis)
    if args.adjudication_out:
        path = write_adjudication_sheet(dis, args.adjudication_out)
        print(f"[wrote] {path}  ({len(dis)} disagreements to adjudicate)")
        print("Fill resolved_category for every row, then rerun with --adjudication.")

    if args.adjudication:
        adjudicated = load_adjudication(args.adjudication)
        consensus = consensus_labels(a, b, adjudicated)
        report["consensus"] = {
            "n": len(consensus),
            "distribution": {k: sum(1 for v in consensus.values() if v == k)
                             for k in sorted(set(consensus.values()))},
            "n_adjudicated": len(adjudicated),
            "clinical_adjudications": sum(1 for d in dis
                                          if d["clinical_judgement_required"]),
        }
        if args.automatic:
            report["automatic_vs_consensus"] = automatic_vs_consensus(consensus, args.automatic)

    print(json.dumps(report, indent=2, default=str))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, default=str))
        print(f"\n[wrote] {args.out}")


if __name__ == "__main__":
    main()
