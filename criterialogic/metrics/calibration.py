"""Calibration & abstention metrics: Expected Calibration Error and selective accuracy."""
from __future__ import annotations


def expected_calibration_error(items, predictions, n_bins: int = 10) -> float:
    """ECE: weighted average gap between confidence and accuracy across equal-width bins."""
    pred_by_id = {p.item_id: p for p in predictions}
    rows = [(pred_by_id[it.item_id].confidence, pred_by_id[it.item_id].label == it.gold) for it in items]
    if not rows:
        return 0.0
    n = len(rows)
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        bucket = [(c, ok) for c, ok in rows if (lo < c <= hi) or (b == 0 and c == 0.0)]
        if not bucket:
            continue
        conf = sum(c for c, _ in bucket) / len(bucket)
        acc = sum(1 for _, ok in bucket if ok) / len(bucket)
        ece += (len(bucket) / n) * abs(acc - conf)
    return ece
def selective_accuracy_curve(items, predictions) -> list[dict]:
    """Accuracy vs coverage: sort by confidence desc, report accuracy on the top-k kept."""
    pred_by_id = {p.item_id: p for p in predictions}
    rows = sorted(
        [(pred_by_id[it.item_id].confidence, pred_by_id[it.item_id].label == it.gold) for it in items],
        key=lambda r: r[0], reverse=True,
    )
    curve, correct = [], 0
    for k, (_, ok) in enumerate(rows, start=1):
        correct += int(ok)
        curve.append({"coverage": k / len(rows), "accuracy": correct / k})
    return curve
