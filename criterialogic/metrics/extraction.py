"""Task A scoring: entity F1, relation F1, and logical-form exact match.
Entity/relation F1 are set-based P/R/F1 over (text, type) and (operator, child)
tuples. Logical-form exact match compares *canonicalised* expressions, so trivial
operand reorderings or double negation do not count as mismatches.
"""
from __future__ import annotations

from criterialogic.metrics.classification import _prf
from criterialogic.schema.logical_form import Atom, BooleanGroup, Expression, LogicalForm, Not, canonicalize


def _set_prf(gold: set, pred: set) -> dict:
    tp = len(gold & pred)
    return _prf(tp, len(pred - gold), len(gold - pred))
def entity_set(expr: Expression) -> set:
    if isinstance(expr, Atom):
        return {(expr.entity.text, expr.entity.type.value)}
    if isinstance(expr, Not):
        return entity_set(expr.operand)
    if isinstance(expr, BooleanGroup):
        out: set = set()
        for op in expr.operands:
            out |= entity_set(op)
        return out
    raise TypeError(type(expr))
def entity_f1(gold: LogicalForm, pred: LogicalForm) -> dict:
    return _set_prf(entity_set(gold.expression), entity_set(pred.expression))
def logical_form_exact_match(gold: LogicalForm, pred: LogicalForm) -> bool:
    """True iff the canonicalised expressions are identical (and polarity matches)."""
    if gold.polarity != pred.polarity:
        return False
    return canonicalize(gold.expression).model_dump_json() == canonicalize(pred.expression).model_dump_json()
