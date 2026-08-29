"""A deliberately negation-blind baseline (illustrative, not for the leaderboard).
It strips NOT nodes and collapses OR to its first operand, so it systematically
makes *negation/polarity* and *logical-composition* errors. Its purpose is to
make the demo's metrics and reasoning-failure taxonomy non-trivial — i.e. to show
the framework detecting and categorising real error patterns.
"""
from __future__ import annotations

from criterialogic.models.base import Model
from criterialogic.oracle import evaluate
from criterialogic.schema.logical_form import Atom, BooleanGroup, BoolOp, Expression, Not
from criterialogic.tasks.base import Item, Prediction


def _strip(expr: Expression) -> Expression:
    if isinstance(expr, Atom):
        return expr
    if isinstance(expr, Not):
        return _strip(expr.operand)  # bug: ignores negation
    if isinstance(expr, BooleanGroup):
        kept = [_strip(op) for op in expr.operands]
        if expr.operator is BoolOp.OR:
            return kept[0]  # bug: treats OR as "first operand only"
        return BooleanGroup(operator=BoolOp.AND, operands=kept)
    raise TypeError(type(expr))
class NegationBlindModel(Model):
    name = "negation_blind"
    def predict(self, item: Item) -> Prediction:
        value = evaluate(_strip(item.criterion.expression), item.facts)
        label = bool(value) if value is not None else False
        return Prediction(item_id=item.item_id, label=label, confidence=0.7)
