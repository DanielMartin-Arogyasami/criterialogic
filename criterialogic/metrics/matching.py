"""n2c2-*style* scoring for Task C: micro & macro F1 over the met/not-met labels,
plus a per-criterion breakdown.
Note on "official" parity: the n2c2 2018 Track-1 organizers' scorer reports
micro- and macro-averaged F1 computed over the per-criterion, per-class results.
The ``overall_macro_f1`` returned here is a macro over the two label *classes*
(met / not-met), which is a defensible but NOT bit-identical statistic. Exact
parity with the released official scorer is a TODO; until then we describe these
as n2c2-style. The per-criterion micro-F1 table is the primary diagnostic the
paper's per-criterion analysis relies on.
"""
from __future__ import annotations

from collections import defaultdict

from criterialogic.metrics.classification import macro_f1, micro_f1, per_class_prf


def matching_scores(items, predictions) -> dict:
    """`items`: list[Item]; `predictions`: list[Prediction] (aligned by item_id)."""
    pred_by_id = {p.item_id: p for p in predictions}
    y_true = [it.gold for it in items]
    y_pred = [pred_by_id[it.item_id].label for it in items]
    # per-criterion micro-F1 (treat "met" as the positive class)
    by_crit_true: dict[str, list] = defaultdict(list)
    by_crit_pred: dict[str, list] = defaultdict(list)
    for it in items:
        by_crit_true[it.group].append(it.gold)
        by_crit_pred[it.group].append(pred_by_id[it.item_id].label)
    per_criterion = {
        tag: {"micro_f1": micro_f1(by_crit_true[tag], by_crit_pred[tag]),
              "n": len(by_crit_true[tag])}
        for tag in sorted(by_crit_true)
    }
    return {
        "overall_micro_f1": micro_f1(y_true, y_pred),
        "overall_macro_f1": macro_f1(y_true, y_pred),
        "n_items": len(items),
        "per_criterion": per_criterion,
        "per_label": per_class_prf(y_true, y_pred),
    }
