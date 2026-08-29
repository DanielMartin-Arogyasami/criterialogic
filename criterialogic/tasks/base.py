"""Shared types for benchmark tasks: Item, Prediction, and a depth utility."""
from __future__ import annotations

from pydantic import BaseModel, Field

from criterialogic.oracle import PatientFacts
from criterialogic.schema.logical_form import Atom, BooleanGroup, Expression, LogicalForm, Not


class Item(BaseModel):
    """One evaluable unit. For matching/compositional: a (criterion, patient) pair."""
    item_id: str
    task: str  # "matching" | "compositional" | "structuring" | "typing_polarity"
    criterion: LogicalForm
    facts: PatientFacts
    gold: bool  # met (True) / not-met (False) under the oracle
    group: str | None = None  # criterion tag (matching) — for per-criterion breakdown
    depth: int | None = None  # logical nesting depth (compositional) — for depth stratification
class Prediction(BaseModel):
    """A model's output for one item: a met/not-met decision + a confidence in [0, 1]."""
    item_id: str
    label: bool
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    abstain: bool = False
    rationale: str | None = None
def expression_depth(expr: Expression) -> int:
    """Logical nesting depth: nested boolean groups. Atom=0, flat AND/OR=1, AND[...OR...]=2."""
    if isinstance(expr, Atom):
        return 0
    if isinstance(expr, Not):
        return expression_depth(expr.operand)
    if isinstance(expr, BooleanGroup):
        return 1 + max(expression_depth(op) for op in expr.operands)
    raise TypeError(f"Unknown node: {type(expr)!r}")
