"""Schema: round-trip, canonicalization, and structural validators."""
import pytest
from pydantic import ValidationError

from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Entity,
    EntityType,
    LogicalForm,
    Not,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
    canonicalize,
    example_nested_compound,
    example_simple_inclusion,
)


def test_round_trip_identical():
    for lf in (example_simple_inclusion(), example_nested_compound()):
        blob = lf.model_dump_json()
        assert LogicalForm.model_validate_json(blob).model_dump_json() == blob
def test_canonicalize_idempotent_and_commutative():
    a = Atom(entity=Entity(text="a", type=EntityType.CONDITION))
    b = Atom(entity=Entity(text="b", type=EntityType.CONDITION))
    g1 = BooleanGroup(operator=BoolOp.AND, operands=[a, b])
    g2 = BooleanGroup(operator=BoolOp.AND, operands=[b, a])
    assert canonicalize(g1).model_dump_json() == canonicalize(g2).model_dump_json()
    c = example_nested_compound().canonical()
    assert c.canonical().model_dump_json() == c.model_dump_json()
def test_double_negation_collapses():
    a = Atom(entity=Entity(text="x", type=EntityType.CONDITION))
    assert isinstance(canonicalize(Not(operand=Not(operand=a))), Atom)
def test_between_requires_upper():
    with pytest.raises((ValidationError, ValueError)):
        NumericConstraint(operator=Comparator.BETWEEN, value=6.5)
def test_numeric_only_on_measurable_entity():
    with pytest.raises((ValidationError, ValueError)):
        Atom(entity=Entity(text="dka", type=EntityType.CONDITION),
             numeric=NumericConstraint(operator=Comparator.GT, value=1))
def test_group_needs_two_operands():
    with pytest.raises((ValidationError, ValueError)):
        BooleanGroup(operator=BoolOp.AND,
                     operands=[Atom(entity=Entity(text="x", type=EntityType.CONDITION))])
def test_windowed_temporal_requires_value_unit():
    with pytest.raises((ValidationError, ValueError)):
        TemporalConstraint(operator=TemporalOp.WITHIN)
