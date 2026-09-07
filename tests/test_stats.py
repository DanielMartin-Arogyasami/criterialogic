"""The statistics behind every reported interval, on hand-checkable cases.

stats.py is imported by file path rather than through the package, because it is
standard-library only by contract and that has to stay testable without pydantic.
"""
import importlib.util
import math
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "cl_stats", Path(__file__).resolve().parents[1] / "criterialogic/metrics/stats.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)


def test_wilson_stays_in_range_at_the_boundaries():
    lo, hi = S.wilson_interval(60, 60)
    assert hi == 1.0 and 0.9 < lo < 1.0, "a perfect score must not get a zero-width interval"
    lo, hi = S.wilson_interval(0, 60)
    assert lo == 0.0 and 0.0 < hi < 0.1
    assert S.wilson_interval(0, 0) == (0.0, 0.0)


def test_wilson_known_value():
    lo, hi = S.wilson_interval(36, 60)  # 0.60, n=60 — the depth-6 cell
    assert abs(lo - 0.4737) < 1e-3 and abs(hi - 0.7143) < 1e-3


def test_spearman_monotone_cases():
    assert S.spearman_rho([1, 2, 3], [3, 2, 1]) == -1.0
    assert S.spearman_rho([1, 2, 3], [1, 2, 3]) == 1.0
    assert S.spearman_rho([1, 2, 3], [5, 5, 5]) == 0.0  # constant -> no correlation


def test_permutation_p_is_exact_and_reports_its_floor():
    out = S.permutation_p([2, 3, 4, 5, 6], [0.95, 0.95, 0.867, 0.717, 0.60])
    assert out["mode"] == "exact" and out["n_permutations"] == 120
    assert abs(out["rho"] + 0.9747) < 1e-3
    assert abs(out["p_one_sided"] - 1 / 60) < 1e-6
    # With five levels no p below 1/120 is attainable; a reader must be able to see that.
    assert abs(out["min_attainable_p"] - 1 / 120) < 1e-9


def test_depth_trend_flags_unresolved_pairs():
    t = S.depth_trend({1: (94, 100), 2: (91, 100), 3: (93, 100), 4: (90, 100)})
    assert t["monotonic_non_increasing"] is False
    assert all(p["cis_overlap"] for p in t["pairwise"]), "flat curve: nothing is separated"
    assert all(p["n_per_depth_needed"] > 0 or p["n_per_depth_needed"] == -1
               for p in t["pairwise"])


def test_selective_accuracy_is_tie_aware():
    # All confidences equal: every coverage level must give the overall accuracy, because
    # ranking by a constant is ranking by list order.
    rows = [(0.7, True)] * 6 + [(0.7, False)] * 4
    curve = S.selective_accuracy(rows)
    assert curve["degenerate_single_bin"] is True
    for pct in ("10%", "50%", "100%"):
        assert abs(curve[pct] - 0.6) < 1e-9


def test_selective_accuracy_rewards_real_confidence():
    rows = [(0.9, True), (0.9, True), (0.5, False), (0.5, False)]
    curve = S.selective_accuracy(rows)
    assert curve["50%"] == 1.0 and curve["100%"] == 0.5
    assert curve["degenerate_single_bin"] is False


def test_ece_zero_when_perfectly_calibrated():
    assert S.expected_calibration_error([(1.0, True), (1.0, True)]) < 1e-9
    # Confident and wrong is the worst case.
    assert abs(S.expected_calibration_error([(1.0, False)]) - 1.0) < 1e-9


def test_kappa_edge_cases():
    assert S.cohens_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert abs(S.cohens_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"])) < 1e-9
    # Both raters used one identical category: chance agreement is total, kappa undefined.
    assert math.isnan(S.cohens_kappa(["a"] * 5, ["a"] * 5))


def test_kappa_ci_brackets_the_point_estimate():
    a = ["x"] * 30 + ["y"] * 20
    b = ["x"] * 27 + ["y"] * 3 + ["y"] * 18 + ["x"] * 2
    out = S.kappa_with_ci(a, b, n_boot=800, seed=3)
    lo, hi = out["ci_95"]
    assert lo <= out["kappa"] <= hi
    assert out["n"] == 50


def test_per_category_agreement_splits_by_category():
    a = ["comp", "comp", "neg"]
    b = ["comp", "neg", "neg"]
    out = S.per_category_agreement(a, b)
    assert set(out) == {"comp", "neg"}
    assert out["comp"]["n_annotator_1"] == 2 and out["comp"]["n_both"] == 1


def test_n_per_group_needed():
    assert S.n_per_group_needed(0.5, 0.5) == -1
    assert S.n_per_group_needed(0.95, 0.60) < S.n_per_group_needed(0.95, 0.867)
