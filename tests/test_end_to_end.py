"""End-to-end: the demo pipeline runs and the diagnostics behave as designed."""
from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.eval.runner import run_task
from criterialogic.models import NegationBlindModel, RuleBasedModel
from criterialogic.tasks.compositional import generate_compositional_items


def test_thirteen_criteria():
    assert len(harmonized_n2c2_criteria()) == 13
def test_matching_pipeline_runs():
    items = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=6, seed=13)
    res = run_task(RuleBasedModel(), items, seed=13)
    assert res["task"] == "matching"
    # rule-based == oracle on structured input -> perfect by construction
    assert res["metrics"]["overall_micro_f1"] == 1.0
    assert res["failure_taxonomy"] == {}
def test_compositional_depth_and_taxonomy():
    items = generate_compositional_items(n_per_depth=10, max_depth=3, seed=29)
    res = run_task(NegationBlindModel(), items, seed=29)
    assert res["task"] == "compositional"
    # the negation-blind model should make attributable errors (taxonomy non-empty)
    assert sum(res["failure_taxonomy"].values()) > 0
    assert set(res["metrics"]["by_depth"]) == {1, 2, 3}
def test_determinism():
    a = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=5, seed=99)
    b = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=5, seed=99)
    assert [i.gold for i in a] == [i.gold for i in b]
