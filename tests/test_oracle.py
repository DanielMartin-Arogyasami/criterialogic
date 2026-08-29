"""Three-valued evaluator semantics."""
from criterialogic.oracle import Fact, PatientFacts, evaluate, is_met
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Entity,
    EntityType,
    Not,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
)


def test_numeric_between_boundaries():
    atom = Atom(entity=Entity(text="HbA1c", type=EntityType.MEASUREMENT),
                numeric=NumericConstraint(operator=Comparator.BETWEEN, value=6.5, upper=9.5, unit="%"))
    facts_in = PatientFacts(record_id="p", facts={"HbA1c": Fact(value=7.2)})
    facts_out = PatientFacts(record_id="p", facts={"HbA1c": Fact(value=10.0)})
    assert evaluate(atom, facts_in) is True
    assert evaluate(atom, facts_out) is False
def test_temporal_window():
    atom = Atom(entity=Entity(text="mi", type=EntityType.CONDITION),
                temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=6, unit=TimeUnit.MONTHS))
    recent = PatientFacts(record_id="p", facts={"mi": Fact(present=True, days_ago=60)})
    old = PatientFacts(record_id="p", facts={"mi": Fact(present=True, days_ago=400)})
    assert evaluate(atom, recent) is True
    assert evaluate(atom, old) is False
def test_unknown_propagates():
    atom = Atom(entity=Entity(text="HbA1c", type=EntityType.MEASUREMENT),
                numeric=NumericConstraint(operator=Comparator.GT, value=7.0))
    empty = PatientFacts(record_id="p", facts={})
    assert evaluate(atom, empty) is None  # absent measurement -> unknown
    assert is_met(_form(atom), empty) is False  # unknown collapses to not-met by default
def test_negation_and_or():
    a = Atom(entity=Entity(text="a", type=EntityType.CONDITION))
    b = Atom(entity=Entity(text="b", type=EntityType.CONDITION))
    facts = PatientFacts(record_id="p", facts={"a": Fact(present=True), "b": Fact(present=False)})
    assert evaluate(Not(operand=a), facts) is False
    assert evaluate(BooleanGroup(operator=BoolOp.OR, operands=[a, b]), facts) is True
    assert evaluate(BooleanGroup(operator=BoolOp.AND, operands=[a, b]), facts) is False
def _form(expr):
    from criterialogic.schema.logical_form import LogicalForm, Polarity, Source
    return LogicalForm(criterion_id="t:1", source=Source.CTGOV_SYNTHETIC,
                       polarity=Polarity.INCLUSION, text="t", expression=expr)
