"""Compositional-arm scoring: accuracy stratified by logical nesting depth.

Depth is the benchmark's independent variable, so this module returns more than a
per-depth mean. Each depth gets a Wilson interval, the curve gets a rank correlation
with an exact permutation p-value, and every pair of depths whose intervals overlap
reports the per-depth n that would separate them.

That last field is the point. The v0.1 draft hypothesised a monotonic decline and the
first run produced 0.68 / 0.58 / 0.60 / 0.58 across depths 1-4 — not monotonic, and with
every interval overlapping. Without the pairwise n, that table can be written up as
supporting a trend. With it, the table says how much more data the claim would need.
"""
from __future__ import annotations

from collections import defaultdict

from criterialogic.metrics.classification import accuracy
from criterialogic.metrics.stats import depth_trend, wilson_interval


def accuracy_by_depth(items, predictions) -> dict:
    pred_by_id = {p.item_id: p for p in predictions}
    correct: dict[int, int] = defaultdict(int)
    totals: dict[int, int] = defaultdict(int)
    n_undepthed = 0
    for it in items:
        if it.depth is None:
            # Refuse to invent a depth. An item with no recorded depth contributes to the
            # overall figure and to nothing else; folding it in under a sentinel value
            # would put a fabricated level into the trend statistics.
            n_undepthed += 1
            continue
        totals[it.depth] += 1
        correct[it.depth] += int(pred_by_id[it.item_id].label == it.gold)

    per_depth = {
        d: {"accuracy": correct[d] / totals[d],
            "n": totals[d],
            "wilson_95": tuple(round(v, 4) for v in wilson_interval(correct[d], totals[d]))}
        for d in sorted(totals)
    }
    all_true = [it.gold for it in items]
    all_pred = [pred_by_id[it.item_id].label for it in items]
    n_correct = sum(1 for t, p in zip(all_true, all_pred) if t == p)

    out = {
        "overall_accuracy": accuracy(all_true, all_pred),
        "overall_wilson_95": tuple(round(v, 4) for v in wilson_interval(n_correct, len(items))),
        "by_depth": per_depth,
        "n_items_without_depth": n_undepthed,
    }
    # A trend needs at least two depth levels; a single-depth set gets the point estimate
    # and its interval, and no correlation dressed up as one.
    if len(totals) >= 2:
        out["trend"] = depth_trend({d: (correct[d], totals[d]) for d in sorted(totals)})
    return out
