"""Task D scoring: accuracy stratified by logical nesting depth.
The headline result the paper reports is how accuracy *degrades* as nesting depth
increases — so we return accuracy per depth plus the overall figure.
"""
from __future__ import annotations

from collections import defaultdict

from criterialogic.metrics.classification import accuracy


def accuracy_by_depth(items, predictions) -> dict:
    pred_by_id = {p.item_id: p for p in predictions}
    by_depth_true: dict[int, list] = defaultdict(list)
    by_depth_pred: dict[int, list] = defaultdict(list)
    for it in items:
        by_depth_true[it.depth].append(it.gold)
        by_depth_pred[it.depth].append(pred_by_id[it.item_id].label)
    per_depth = {
        d: {"accuracy": accuracy(by_depth_true[d], by_depth_pred[d]), "n": len(by_depth_true[d])}
        for d in sorted(by_depth_true)
    }
    all_true = [it.gold for it in items]
    all_pred = [pred_by_id[it.item_id].label for it in items]
    return {"overall_accuracy": accuracy(all_true, all_pred), "by_depth": per_depth}
