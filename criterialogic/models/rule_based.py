"""Rule-based baseline — the deterministic floor of the ladder.
It evaluates the *already-structured* LogicalForm against the patient facts with
the oracle's three-valued logic. On structured synthetic input it is effectively
an oracle (≈ perfect); on real text it would first require Task-A parsing, which
is where rule-based systems lose ground. Confidence is 1.0 for decided cases and
0.5 for unknowns (which it resolves to not-met).
"""
from __future__ import annotations

from criterialogic.models.base import Model
from criterialogic.oracle import evaluate
from criterialogic.tasks.base import Item, Prediction


class RuleBasedModel(Model):
    name = "rule_based"
    def predict(self, item: Item) -> Prediction:
        value = evaluate(item.criterion.expression, item.facts)
        if value is None:
            return Prediction(item_id=item.item_id, label=False, confidence=0.5,
                              abstain=False, rationale="unknown -> not met")
        return Prediction(item_id=item.item_id, label=value, confidence=1.0)
