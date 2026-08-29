"""oracle.py — deterministic ground-truth evaluator for a LogicalForm.
Given a structured ``PatientFacts`` record, ``evaluate`` decides whether a
criterion's logical expression is satisfied. It serves two roles:
1. The **ground-truth oracle** for the synthetic Task C/D items (the label a
   perfect system should produce).
2. The engine behind the **rule-based baseline** (the deterministic floor of
   the baseline ladder), which evaluates an already-structured form.
Three-valued logic is used: a leaf whose fact is absent evaluates to ``None``
(*unknown*). ``None`` propagates through AND/OR with Kleene semantics so that
"unknown" is never silently treated as "not met".
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Expression,
    LogicalForm,
    Not,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
)

_TO_DAYS = {TimeUnit.DAYS: 1.0, TimeUnit.WEEKS: 7.0, TimeUnit.MONTHS: 30.4375, TimeUnit.YEARS: 365.25}
class Fact(BaseModel):
    """A single structured fact about a patient, keyed by entity surface text."""
    present: bool = True
    value: float | None = None  # measured value for measurement/observation/person entities
    days_ago: float | None = None  # recency of the most recent occurrence, relative to anchor
    current: bool = False  # is the state ongoing/active at the anchor
class PatientFacts(BaseModel):
    """A synthetic (or harmonized) structured patient record: entity text -> Fact."""
    record_id: str
    facts: dict[str, Fact] = Field(default_factory=dict)
    def get(self, entity_text: str) -> Fact | None:
        return self.facts.get(entity_text)
# --------------------------------------------------------------------------- #
# Kleene three-valued connectives
# --------------------------------------------------------------------------- #
def _and(values: list[bool | None]) -> bool | None:
    if any(v is False for v in values):
        return False
    if any(v is None for v in values):
        return None
    return True
def _or(values: list[bool | None]) -> bool | None:
    if any(v is True for v in values):
        return True
    if any(v is None for v in values):
        return None
    return False
def _check_numeric(c: NumericConstraint, x: float) -> bool:
    if c.operator is Comparator.LT:
        return x < c.value
    if c.operator is Comparator.LE:
        return x <= c.value
    if c.operator is Comparator.GT:
        return x > c.value
    if c.operator is Comparator.GE:
        return x >= c.value
    if c.operator is Comparator.EQ:
        return x == c.value
    if c.operator is Comparator.NE:
        return x != c.value
    if c.operator is Comparator.BETWEEN:
        lo = x >= c.value if c.lower_inclusive else x > c.value
        hi = x <= c.upper if c.upper_inclusive else x < c.upper
        return lo and hi
    raise ValueError(f"Unhandled comparator {c.operator}")
def _check_temporal(t: TemporalConstraint, fact: Fact) -> bool | None:
    if t.operator is TemporalOp.CURRENT:
        return fact.current
    if t.operator is TemporalOp.ANY_HISTORY:
        return fact.present
    # windowed operators need a recency
    if fact.days_ago is None:
        return None
    window_days = (t.value or 0) * _TO_DAYS[t.unit]
    if t.operator in (TemporalOp.WITHIN, TemporalOp.BEFORE, TemporalOp.FOR_AT_MOST):
        return fact.days_ago <= window_days
    if t.operator in (TemporalOp.AFTER, TemporalOp.FOR_AT_LEAST):
        return fact.days_ago >= window_days
    raise ValueError(f"Unhandled temporal operator {t.operator}")
def _eval_atom(atom: Atom, facts: PatientFacts) -> bool | None:
    fact = facts.get(atom.entity.text)
    if fact is None or not fact.present:
        # numeric/temporal questions about an absent entity are unknown vs. false:
        # an absent condition is "not met" (False); an absent measurement is "unknown" (None).
        if fact is None and atom.numeric is not None:
            return None
        return False
    result: bool | None = True
    if atom.numeric is not None:
        if fact.value is None:
            return None
        result = _and([result, _check_numeric(atom.numeric, fact.value)])
    if atom.temporal is not None:
        result = _and([result, _check_temporal(atom.temporal, fact)])
    return result
def evaluate(expr: Expression, facts: PatientFacts) -> bool | None:
    """Three-valued evaluation of an expression against patient facts."""
    if isinstance(expr, Atom):
        return _eval_atom(expr, facts)
    if isinstance(expr, Not):
        inner = evaluate(expr.operand, facts)
        return None if inner is None else (not inner)
    if isinstance(expr, BooleanGroup):
        vals = [evaluate(op, facts) for op in expr.operands]
        return _and(vals) if expr.operator is BoolOp.AND else _or(vals)
    raise TypeError(f"Unknown expression node: {type(expr)!r}")
def is_met(form: LogicalForm, facts: PatientFacts, unknown_is_met: bool = False) -> bool:
    """Collapse three-valued evaluation to a met/not-met decision.
    Polarity is preserved upstream; this returns truth of the *expression*.
    Unknown resolves to ``unknown_is_met`` (default: not met).
    """
    v = evaluate(form.expression, facts)
    return unknown_is_met if v is None else v
