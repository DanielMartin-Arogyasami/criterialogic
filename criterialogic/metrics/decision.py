"""Met / not-met scoring for the real-criteria arm.

Micro- and macro-F1 over the two label classes plus a per-group breakdown, where the
group is the source trial. Nothing here claims parity with any external scorer: v0.1
described these as "n2c2-style" with exact parity marked TODO, and since the n2c2
component is gone (docs/V2_SCOPE.md) the comparison would be to a scorer the benchmark
no longer uses. These are the benchmark's own definitions, stated plainly:

* ``overall_micro_f1``  F1 pooled over all items, "met" as the positive class.
* ``overall_macro_f1``  unweighted mean of the per-class F1s (met, not-met).
* ``per_group``         micro-F1 within each source trial.
* ``per_label``         precision/recall/F1/support per class.

The class balance is reported because F1 on a set that is 60% "met" is not comparable to
F1 on a balanced one, and the gold met-rate here is a property of the seeded patient
sampler rather than of anything clinical.
"""
from __future__ import annotations

from collections import defaultdict

from criterialogic.metrics.classification import macro_f1, micro_f1, per_class_prf
from criterialogic.metrics.stats import wilson_interval


def decision_scores(items, predictions) -> dict:
    """`items`: list[Item]; `predictions`: list[Prediction] (aligned by item_id)."""
    pred_by_id = {p.item_id: p for p in predictions}
    y_true = [it.gold for it in items]
    y_pred = [pred_by_id[it.item_id].label for it in items]

    by_group_true: dict[str, list] = defaultdict(list)
    by_group_pred: dict[str, list] = defaultdict(list)
    for it in items:
        key = it.group or "ungrouped"
        by_group_true[key].append(it.gold)
        by_group_pred[key].append(pred_by_id[it.item_id].label)

    n_correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return {
        "overall_micro_f1": micro_f1(y_true, y_pred),
        "overall_macro_f1": macro_f1(y_true, y_pred),
        "overall_accuracy": n_correct / len(items) if items else 0.0,
        "overall_wilson_95": tuple(round(v, 4) for v in wilson_interval(n_correct, len(items))),
        "n_items": len(items),
        "gold_met_rate": round(sum(1 for t in y_true if t) / len(y_true), 4) if y_true else 0.0,
        "n_groups": len(by_group_true),
        "per_group": {
            g: {"micro_f1": micro_f1(by_group_true[g], by_group_pred[g]),
                "n": len(by_group_true[g])}
            for g in sorted(by_group_true)
        },
        "per_label": per_class_prf(y_true, y_pred),
    }


# v0.1 name, kept so an existing submission scorer does not break on the rename.
matching_scores = decision_scores
