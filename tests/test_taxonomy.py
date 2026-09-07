"""The heuristic labeller: decision order, unanswerability, reachable categories."""
from criterialogic.oracle import Fact, PatientFacts
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
    Polarity,
    Source,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
)
from criterialogic.tasks.base import Item, Prediction
from criterialogic.taxonomy.annotate import (
    HUMAN_ONLY_CATEGORIES,
    categorize_error,
    failure_breakdown,
    is_unanswerable,
    reachable_categories,
)
from criterialogic.taxonomy.categories import FailureCategory


def _item(expr, facts, gold, item_id="t:0", depth=None):
    form = LogicalForm(criterion_id="test:1", source=Source.SYNTHETIC_EXAMPLE,
                       polarity=Polarity.INCLUSION, text="test", expression=expr)
    return Item(item_id=item_id, task="compositional", criterion=form,
                facts=PatientFacts(record_id="r", facts=facts), gold=gold, depth=depth)


def test_negation_probe_fires_before_composition():
    """A nested criterion whose error is explained by dropping the NOT is negation."""
    stroke = Atom(entity=Entity(text="stroke", type=EntityType.CONDITION))
    other = Atom(entity=Entity(text="asthma", type=EntityType.CONDITION))
    expr = BooleanGroup(operator=BoolOp.AND, operands=[Not(operand=stroke), other])
    facts = {"stroke": Fact(present=True), "asthma": Fact(present=True)}
    item = _item(expr, facts, gold=False, depth=1)
    pred = Prediction(item_id=item.item_id, label=True, confidence=0.9)
    assert categorize_error(item, pred) is FailureCategory.NEGATION_POLARITY


def test_temporal_probe_fires_on_a_nested_criterion():
    """v1 would have called this logical_composition purely because it is nested."""
    mi = Atom(entity=Entity(text="mi", type=EntityType.CONDITION),
              temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=6,
                                          unit=TimeUnit.MONTHS))
    asthma = Atom(entity=Entity(text="asthma", type=EntityType.CONDITION))
    expr = BooleanGroup(operator=BoolOp.AND, operands=[mi, asthma])
    facts = {"mi": Fact(present=True, days_ago=400.0), "asthma": Fact(present=True)}
    item = _item(expr, facts, gold=False, depth=1)
    pred = Prediction(item_id=item.item_id, label=True, confidence=0.8)
    assert categorize_error(item, pred) is FailureCategory.TEMPORAL


def test_numeric_probe_fires_on_a_nested_criterion():
    hba1c = Atom(entity=Entity(text="hba1c", type=EntityType.MEASUREMENT),
                 numeric=NumericConstraint(operator=Comparator.BETWEEN, value=6.5,
                                           upper=9.5, unit="%"))
    asthma = Atom(entity=Entity(text="asthma", type=EntityType.CONDITION))
    expr = BooleanGroup(operator=BoolOp.AND, operands=[hba1c, asthma])
    facts = {"hba1c": Fact(present=True, value=11.0), "asthma": Fact(present=True)}
    item = _item(expr, facts, gold=False, depth=1)
    pred = Prediction(item_id=item.item_id, label=True, confidence=0.8)
    assert categorize_error(item, pred) is FailureCategory.NUMERIC_THRESHOLD


def test_composition_is_the_residual_not_the_default():
    """An OR read as an AND: no single-feature probe explains it."""
    a = Atom(entity=Entity(text="a", type=EntityType.CONDITION))
    b = Atom(entity=Entity(text="b", type=EntityType.CONDITION))
    expr = BooleanGroup(operator=BoolOp.OR, operands=[a, b])
    facts = {"a": Fact(present=True), "b": Fact(present=False)}
    item = _item(expr, facts, gold=True, depth=1)
    pred = Prediction(item_id=item.item_id, label=False, confidence=0.7)
    assert categorize_error(item, pred) is FailureCategory.LOGICAL_COMPOSITION


def test_flat_unexplained_error_is_unattributed_not_guessed():
    """v1 guessed implicit_knowledge here; no counterfactual supports that."""
    a = Atom(entity=Entity(text="a", type=EntityType.CONDITION))
    item = _item(a, {"a": Fact(present=True)}, gold=True, depth=0)
    pred = Prediction(item_id=item.item_id, label=False, confidence=0.6)
    assert categorize_error(item, pred) is FailureCategory.NONE


def test_unanswerable_detects_the_currency_render_defect():
    aspirin = Atom(entity=Entity(text="aspirin", type=EntityType.DRUG),
                   temporal=TemporalConstraint(operator=TemporalOp.CURRENT))
    # present but not current: renderer v1 shows only "present", so the prompt cannot
    # distinguish this from "currency never recorded", yet gold says not met.
    item = _item(aspirin, {"aspirin": Fact(present=True, current=False)}, gold=False)
    assert is_unanswerable(item) is True
    # current=True is answerable, and so is an absent fact.
    assert is_unanswerable(_item(aspirin, {"aspirin": Fact(present=True, current=True)},
                                 gold=True)) is False
    assert is_unanswerable(_item(aspirin, {}, gold=False)) is False


def test_unanswerable_errors_are_withheld_from_the_distribution():
    aspirin = Atom(entity=Entity(text="aspirin", type=EntityType.DRUG),
                   temporal=TemporalConstraint(operator=TemporalOp.CURRENT))
    item = _item(aspirin, {"aspirin": Fact(present=True, current=False)}, gold=False)
    pred = Prediction(item_id=item.item_id, label=True, confidence=0.9)
    out = failure_breakdown([item], [pred])
    assert out["n_errors"] == 1
    assert out["n_errors_unanswerable"] == 1
    assert out["n_errors_scored"] == 0, "an unanswerable item is not evidence about reasoning"
    assert out["unanswerable_categories_withheld"]
    # And it can be included explicitly when someone wants the raw count.
    assert failure_breakdown([item], [pred], exclude_unanswerable=False)["n_errors_scored"] == 1


def test_rationale_clustering_is_reported():
    a = Atom(entity=Entity(text="a", type=EntityType.CONDITION))
    b = Atom(entity=Entity(text="b", type=EntityType.CONDITION))
    expr = BooleanGroup(operator=BoolOp.OR, operands=[a, b])
    facts = {"a": Fact(present=True), "b": Fact(present=False)}
    items, preds = [], []
    for i in range(3):
        it = _item(expr, facts, gold=True, item_id=f"t:{i}", depth=1)
        items.append(it)
        preds.append(Prediction(item_id=it.item_id, label=False, confidence=0.7,
                                rationale="a is not satisfied"))
    out = failure_breakdown(items, preds)
    assert out["n_errors"] == 3 and out["distinct_rationales"] == 1
    assert out["largest_rationale_cluster"] == 3


def test_human_only_categories_are_declared():
    assert HUMAN_ONLY_CATEGORIES.isdisjoint(reachable_categories())
    assert FailureCategory.FABRICATION in HUMAN_ONLY_CATEGORIES
    assert FailureCategory.ENTITY_CONFLATION in HUMAN_ONLY_CATEGORIES
    assert FailureCategory.IMPLICIT_KNOWLEDGE in HUMAN_ONLY_CATEGORIES
