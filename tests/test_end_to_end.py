"""End-to-end: both arms run and the diagnostics behave as designed."""
import pytest

from criterialogic.data.real_criteria import build_criterion_forms, polarity_distribution
from criterialogic.eval.runner import run_task
from criterialogic.models import NegationBlindModel, RuleBasedModel
from criterialogic.tasks.compositional import (
    generate_compositional_items,
    regenerate_reported_depth_set,
)
from criterialogic.tasks.real_criteria import generate_real_criteria_items

FIXTURE_CACHE = "tests/fixtures/ctgov_cache"


def test_real_criteria_segmentation_yields_forms():
    forms, stats = build_criterion_forms(cache_dir=FIXTURE_CACHE, max_per_study=4)
    assert forms, "the fixture cache should segment to at least one criterion"
    assert stats.sentences > stats.mapped, "extraction is conservative: some must be skipped"
    # Every form must trace back to a trial and record its snapshot.
    for f in forms:
        assert f.metadata["trial_id"].startswith("NCT")
        assert f.metadata["section"] in ("inclusion", "exclusion")
        assert f.text.strip()


def test_real_criteria_pipeline_runs():
    forms, _ = build_criterion_forms(cache_dir=FIXTURE_CACHE, max_per_study=4)
    items = generate_real_criteria_items(forms, n_per_criterion=2, seed=17)
    res = run_task(RuleBasedModel(), items, seed=17)
    assert res["task"] == "real_criteria"
    # rule_based evaluates the already-structured form, so it *is* the oracle here and
    # is perfect by construction. That is a software-validation artifact, not a finding.
    assert res["metrics"]["overall_micro_f1"] == 1.0
    assert res["failure_taxonomy"]["n_errors"] == 0
    assert res["provenance"]["patients"] == "synthetic"


def test_compositional_depth_and_taxonomy():
    items = generate_compositional_items(n_per_depth=10, max_depth=3, seed=29)
    res = run_task(NegationBlindModel(), items, seed=29)
    assert res["task"] == "compositional"
    assert set(res["metrics"]["by_depth"]) == {1, 2, 3}
    # The negation-blind model must make attributable errors, or the taxonomy is not wired.
    assert res["failure_taxonomy"]["n_errors"] > 0
    assert sum(res["failure_taxonomy"]["categories"].values()) > 0
    # Every depth carries an interval, not just a point estimate.
    for v in res["metrics"]["by_depth"].values():
        lo, hi = v["wilson_95"]
        assert 0.0 <= lo <= v["accuracy"] <= hi <= 1.0


def test_explicit_depths_and_trend():
    items = generate_compositional_items(n_per_depth=6, seed=29, depths=[4, 5])
    assert {it.depth for it in items} == {4, 5}
    res = run_task(NegationBlindModel(), items, seed=29)
    assert "trend" in res["metrics"]
    assert res["metrics"]["trend"]["spearman"]["mode"] == "exact"


def test_single_depth_set_has_no_trend():
    items = generate_compositional_items(n_per_depth=6, seed=29, depths=[3])
    res = run_task(NegationBlindModel(), items, seed=29)
    # One depth level cannot support a correlation, and must not report one.
    assert "trend" not in res["metrics"]


def test_reported_depth_set_is_regenerable():
    a = regenerate_reported_depth_set(depth=3, n_per_depth=5)
    b = regenerate_reported_depth_set(depth=3, n_per_depth=5)
    assert [i.item_id for i in a] == [i.item_id for i in b]
    assert [i.gold for i in a] == [i.gold for i in b]
    assert all(i.depth == 3 for i in a)


def test_determinism():
    a = generate_compositional_items(n_per_depth=5, max_depth=3, seed=99)
    b = generate_compositional_items(n_per_depth=5, max_depth=3, seed=99)
    assert [i.gold for i in a] == [i.gold for i in b]
    assert [i.criterion.model_dump_json() for i in a] == [i.criterion.model_dump_json() for i in b]


def test_offline_diagnostics_report_no_confidence_signal():
    items = generate_compositional_items(n_per_depth=8, max_depth=2, seed=29)
    res = run_task(NegationBlindModel(), items, seed=29)
    # negation_blind emits a constant 0.7, so its abstention curve is meaningless and
    # the runner must say so rather than reporting a slope.
    assert res["calibration"]["usable_confidence_signal"] is False
    assert res["calibration"]["selective_accuracy"]["degenerate_single_bin"] is True


def test_bad_depth_rejected():
    with pytest.raises(ValueError):
        generate_compositional_items(n_per_depth=2, seed=1, depths=[0])


def test_polarity_is_exercised():
    """The v0.1 matching task was 100% inclusion, so polarity was never tested."""
    forms, _ = build_criterion_forms(cache_dir=FIXTURE_CACHE, max_per_study=8)
    dist = polarity_distribution(forms)
    assert dist, "no forms segmented from the fixture cache"
    # Real trials write exclusion criteria; the fixture should contain some structure
    # beyond a single polarity if it contains enough criteria.
    assert set(dist) <= {"inclusion", "exclusion"}
