"""Structural counts behind the per-depth table (reviewer request: what else changes with depth)."""
from criterialogic.metrics.structure import (
    balanced_accuracy,
    currency_ambiguous_leaves,
    expression_stats,
    leaf_atoms,
    pearson_r,
    undocumented_leaves,
)
from criterialogic.oracle import Fact, PatientFacts
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Entity,
    EntityType,
    Not,
    TemporalConstraint,
    TemporalOp,
)


def _atom(text, temporal=None):
    return Atom(entity=Entity(text=text, type=EntityType.CONDITION), temporal=temporal)


def _expr():
    # AND[ AND[a, NOT OR[b, c]], d ]: nominal depth 3, four leaves, one NOT.
    inner_or = BooleanGroup(operator=BoolOp.OR, operands=[_atom("b"), _atom("c")])
    inner_and = BooleanGroup(operator=BoolOp.AND, operands=[_atom("a"), Not(operand=inner_or)])
    timed = _atom("d", TemporalConstraint(operator=TemporalOp.ANY_HISTORY))
    return BooleanGroup(operator=BoolOp.AND, operands=[inner_and, timed])


def test_expression_stats_counts_and_canonical_depth():
    s = expression_stats(_expr())
    assert (s["leaves"], s["and_groups"], s["or_groups"], s["nots"], s["groups"]) == (4, 2, 1, 1, 3)
    assert s["depth"] == 3
    # The inner AND sits directly inside an AND, so canonicalisation flattens one level.
    assert s["canonical_depth"] == 2
    assert [a.entity.text for a in leaf_atoms(_expr())] == ["a", "b", "c", "d"]


def test_undocumented_and_currency_ambiguous_leaves():
    facts = PatientFacts(record_id="r", facts={
        "a": Fact(present=True, current=False),   # untimed, present, not current -> ambiguous
        "b": Fact(present=False),                 # documented absent -> not ambiguous
        "d": Fact(present=True, current=False),   # timed atom -> not ambiguous
    })
    assert undocumented_leaves(_expr(), facts) == 1          # "c"
    assert currency_ambiguous_leaves(_expr(), facts) == 1    # "a"


def test_balanced_accuracy_puts_a_constant_answer_at_chance():
    rows = [(True, True)] * 40 + [(False, True)] * 60     # always "met", 40% met
    assert balanced_accuracy(rows) == 0.5
    assert balanced_accuracy([(True, True)] * 3) is None


def test_pearson_r_basic():
    assert abs(pearson_r([1, 2, 3], [2, 4, 6]) - 1.0) < 1e-12
    assert pearson_r([1, 1, 1], [1, 2, 3]) == 0.0
