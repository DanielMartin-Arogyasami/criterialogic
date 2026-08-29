"""Taxonomy reliability metrics + annotation CSV round-trip."""
import csv

from criterialogic.models import NegationBlindModel
from criterialogic.tasks.compositional import generate_compositional_items
from criterialogic.taxonomy.reliability import (
    cohens_kappa,
    export_error_set,
    human_vs_automatic,
    load_labels,
    percent_agreement,
)
from criterialogic.taxonomy.reliability import (
    test_retest as intra_retest,
)


def test_cohens_kappa_known_values():
    assert abs(cohens_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"])) < 1e-9  # chance-level -> 0
    assert cohens_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0                 # perfect -> 1
    assert abs(percent_agreement(["a", "a", "b"], ["a", "b", "b"]) - 2 / 3) < 1e-9
def _errors():
    items = generate_compositional_items(n_per_depth=8, max_depth=3, seed=29)
    preds = NegationBlindModel().predict_batch(items)
    return items, preds
def test_export_and_load_roundtrip(tmp_path):
    items, preds = _errors()
    out = tmp_path / "errors.csv"
    summary = export_error_set(items, preds, str(out))
    assert summary["n_errors"] > 0 and out.exists()
    assert load_labels(str(out)) == {}  # blank human_category on export
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    for r in rows:  # simulate a perfect human pass
        r["human_category"] = r["automatic_category"]
    annotated = tmp_path / "annotated.csv"
    with open(annotated, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    hv = human_vs_automatic(items, preds, load_labels(str(annotated)))
    assert hv["n"] == summary["n_errors"] and hv["cohens_kappa"] == 1.0
def test_test_retest_identical_passes():
    labels = {"comp:d1:000": "temporal", "comp:d2:001": "logical_composition"}
    tr = intra_retest(labels, {**labels})
    assert tr["cohens_kappa"] == 1.0 and tr["n"] == 2
