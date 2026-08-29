"""Heuristic error labelling for the demo's per-model failure breakdown.
IMPORTANT: this is a *heuristic aid* for error triage, not the released gold
taxonomy. The paper's taxonomy is produced by human annotation with reported
inter-annotator agreement (spec §6); these heuristics pre-sort errors to make
that human pass cheaper, and they drive the demo's illustrative breakdown.
The heuristics work by counterfactual probing on the structured form: if
*ignoring negation* would have fixed the error -> NEGATION_POLARITY; if the only
constraints involved are temporal/numeric -> TEMPORAL / NUMERIC_THRESHOLD; if a
compound (depth >= 1) is involved -> LOGICAL_COMPOSITION; else UNATTRIBUTED.
"""
from __future__ import annotations

from collections import Counter

from criterialogic.oracle import evaluate
from criterialogic.schema.logical_form import Atom, BooleanGroup, Expression, Not
from criterialogic.tasks.base import expression_depth
from criterialogic.taxonomy.categories import FailureCategory


def _has(expr: Expression, attr: str) -> bool:
    if isinstance(expr, Atom):
        return getattr(expr, attr) is not None
    if isinstance(expr, Not):
        return _has(expr.operand, attr)
    if isinstance(expr, BooleanGroup):
        return any(_has(op, attr) for op in expr.operands)
    return False
def _contains_not(expr: Expression) -> bool:
    if isinstance(expr, Not):
        return True
    if isinstance(expr, BooleanGroup):
        return any(_contains_not(op) for op in expr.operands)
    return False
def _strip_negation(expr: Expression) -> Expression:
    if isinstance(expr, Atom):
        return expr
    if isinstance(expr, Not):
        return _strip_negation(expr.operand)
    if isinstance(expr, BooleanGroup):
        return BooleanGroup(operator=expr.operator, operands=[_strip_negation(o) for o in expr.operands])
    raise TypeError(type(expr))
def categorize_error(item, prediction) -> FailureCategory:
    """Return a heuristic failure category for one (item, prediction)."""
    if prediction.label == item.gold:
        return FailureCategory.NONE
    expr = item.criterion.expression
    # Would ignoring negation have produced the model's (wrong) answer? -> negation flip
    if _contains_not(expr):
        stripped = evaluate(_strip_negation(expr), item.facts)
        if stripped is not None and bool(stripped) == prediction.label:
            return FailureCategory.NEGATION_POLARITY
    depth = expression_depth(expr)
    if depth >= 1:
        return FailureCategory.LOGICAL_COMPOSITION
    if _has(expr, "temporal") and not _has(expr, "numeric"):
        return FailureCategory.TEMPORAL
    if _has(expr, "numeric"):
        return FailureCategory.NUMERIC_THRESHOLD
    return FailureCategory.IMPLICIT_KNOWLEDGE
def failure_breakdown(items, predictions) -> dict[str, int]:
    """Counter of failure categories over the error set (correct items -> NONE excluded)."""
    pred_by_id = {p.item_id: p for p in predictions}
    counts = Counter(
        categorize_error(it, pred_by_id[it.item_id]).value
        for it in items
        if pred_by_id[it.item_id].label != it.gold
    )
    return dict(counts)
