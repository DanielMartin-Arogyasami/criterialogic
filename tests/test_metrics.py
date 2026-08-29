"""Metric correctness on tiny hand-computed cases."""
from criterialogic.metrics.classification import accuracy, macro_f1, micro_f1, per_class_prf


def test_perfect_scores():
    y = [True, False, True, False]
    assert micro_f1(y, y) == 1.0
    assert macro_f1(y, y) == 1.0
    assert accuracy(y, y) == 1.0
def test_micro_f1_equals_accuracy_single_label():
    # For single-label data, micro-F1 == accuracy. Only item 0 is correct -> 1/3.
    yt = [True, True, False]
    yp = [True, False, True]
    assert abs(micro_f1(yt, yp) - 1 / 3) < 1e-9
    assert abs(accuracy(yt, yp) - 1 / 3) < 1e-9
def test_per_class_positive_f1():
    # Positive ("True") class: 1 TP, 1 FP, 1 FN -> P=R=F1=0.5
    yt = [True, True, False]
    yp = [True, False, True]
    assert abs(per_class_prf(yt, yp)[True]["f1"] - 0.5) < 1e-9
