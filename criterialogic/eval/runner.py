"""Orchestrates a full evaluation: run a model over a task's items, compute metrics,
attach the failure-taxonomy breakdown and reproducibility metadata.
"""
from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone

from criterialogic.metrics.calibration import expected_calibration_error, selective_accuracy_curve
from criterialogic.metrics.logic import accuracy_by_depth
from criterialogic.metrics.matching import matching_scores
from criterialogic.taxonomy.annotate import failure_breakdown


def run_task(model, items, seed: int | None = None) -> dict:
    """Evaluate `model` on `items` (one task). Returns a result dict ready to serialise."""
    if not items:
        raise ValueError("No items to evaluate.")
    task = items[0].task
    predictions = model.predict_batch(items)
    result: dict = {
        "task": task,
        "model": model.info(),
        "n_items": len(items),
        "metrics": {},
        "failure_taxonomy": failure_breakdown(items, predictions),
        "calibration": {
            "ece": expected_calibration_error(items, predictions),
        },
        "repro": {
            "seed": seed,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }
    if task == "matching":
        result["metrics"] = matching_scores(items, predictions)
    elif task == "compositional":
        result["metrics"] = accuracy_by_depth(items, predictions)
    else:
        # generic accuracy for other tasks
        from criterialogic.metrics.classification import accuracy
        pred_by_id = {p.item_id: p for p in predictions}
        result["metrics"] = {
            "accuracy": accuracy([it.gold for it in items],
                                 [pred_by_id[it.item_id].label for it in items])
        }
    # keep a small slice of the selective-accuracy curve for the report
    curve = selective_accuracy_curve(items, predictions)
    result["calibration"]["selective_accuracy_at_50pct_coverage"] = next(
        (pt["accuracy"] for pt in curve if pt["coverage"] >= 0.5), None
    )
    return result
