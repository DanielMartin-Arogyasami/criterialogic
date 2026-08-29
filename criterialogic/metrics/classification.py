"""Precision / recall / F1 for binary and multi-class labels (no sklearn dependency)."""
from __future__ import annotations

from collections import defaultdict


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"precision": p, "recall": r, "f1": f, "support": tp + fn}
def per_class_prf(y_true: list, y_pred: list) -> dict:
    """Per-class precision/recall/F1 over arbitrary hashable labels."""
    assert len(y_true) == len(y_pred)
    tp: defaultdict = defaultdict(int)
    fp: defaultdict = defaultdict(int)
    fn: defaultdict = defaultdict(int)
    labels = set(y_true) | set(y_pred)
    for t, p in zip(y_true, y_pred):
        if t == p:
            tp[t] += 1
        else:
            fp[p] += 1
            fn[t] += 1
    return {lab: _prf(tp[lab], fp[lab], fn[lab]) for lab in sorted(labels, key=str)}
def macro_f1(y_true: list, y_pred: list) -> float:
    per = per_class_prf(y_true, y_pred)
    return sum(v["f1"] for v in per.values()) / len(per) if per else 0.0
def micro_f1(y_true: list, y_pred: list) -> float:
    tp = fp = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == p:
            tp += 1
        else:
            fp += 1
            fn += 1
    return _prf(tp, fp, fn)["f1"]
def accuracy(y_true: list, y_pred: list) -> float:
    if not y_true:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
