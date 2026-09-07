"""The two-annotator workflow: blind export, agreement, adjudication, consensus."""
import csv

import pytest

from criterialogic.models import NegationBlindModel
from criterialogic.tasks.compositional import generate_compositional_items
from criterialogic.taxonomy.reliability import (
    ANNOTATOR_COLUMNS,
    agreement_report,
    automatic_vs_consensus,
    consensus_labels,
    disagreements,
    export_for_annotation,
    load_adjudication,
    load_annotations,
    sample_error_set,
    write_adjudication_sheet,
)


def _runs():
    items = generate_compositional_items(n_per_depth=10, max_depth=3, seed=29)
    return {"compositional::negation_blind": (items, NegationBlindModel().predict_batch(items))}


def test_sample_is_stratified_and_deterministic():
    runs = _runs()
    a = sample_error_set(runs, n=12, seed=5)
    b = sample_error_set(runs, n=12, seed=5)
    assert a and [r["item_id"] for r in a] == [r["item_id"] for r in b]
    assert all(r["_unanswerable"] == "no" for r in a), "unanswerable items excluded by default"


def test_export_is_blind_to_the_automatic_labeller(tmp_path):
    sample = sample_error_set(_runs(), n=10, seed=5)
    info = export_for_annotation(sample, tmp_path)
    assert len(info["annotator_files"]) == 2
    for path in info["annotator_files"]:
        header = next(csv.reader(open(path, encoding="utf-8")))
        assert "automatic_category" not in header, "annotators must not see the heuristic label"
        for col in ANNOTATOR_COLUMNS:
            assert col in header
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        assert all(r["category"] == "" for r in rows), "exported blank for the annotator"
    # The automatic labels exist, but held back in a separate file.
    held = list(csv.DictReader(open(info["held_back_automatic_labels"], encoding="utf-8")))
    assert held and all(r["automatic_category"] for r in held)


def _write(path, rows, extra=None):
    fields = ["item_id", "arm", "depth", "category", "clinical_judgement_required", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({**{f: "" for f in fields}, **r, **(extra or {})})


def test_agreement_report_slices_by_arm_and_clinical_flag(tmp_path):
    a_path, b_path = tmp_path / "a.csv", tmp_path / "b.csv"
    _write(a_path, [
        {"item_id": "1", "arm": "compositional", "depth": "2", "category": "logical_composition"},
        {"item_id": "2", "arm": "compositional", "depth": "3", "category": "negation_polarity"},
        {"item_id": "3", "arm": "real_criteria", "depth": "0", "category": "entity_conflation",
         "clinical_judgement_required": "yes"},
    ])
    _write(b_path, [
        {"item_id": "1", "arm": "compositional", "depth": "2", "category": "logical_composition"},
        {"item_id": "2", "arm": "compositional", "depth": "3", "category": "negation_polarity"},
        {"item_id": "3", "arm": "real_criteria", "depth": "0", "category": "implicit_knowledge",
         "clinical_judgement_required": "yes"},
    ])
    a, b = load_annotations(a_path), load_annotations(b_path)
    rep = agreement_report(a, b, n_boot=200)
    assert rep["n_shared_items"] == 3
    assert set(rep["by_arm"]) == {"compositional", "real_criteria"}
    # The compositional arm has no clinical content, so agreement there measures the
    # taxonomy itself. Here it is perfect and the real-criteria slice is not.
    assert rep["by_arm"]["compositional"]["percent_agreement"] == 1.0
    assert rep["by_arm"]["real_criteria"]["percent_agreement"] == 0.0
    assert rep["clinical_judgement"]["n_flagged"] == 1
    assert abs(rep["clinical_judgement"]["fraction_flagged"] - round(1 / 3, 4)) < 1e-9
    assert rep["meets_minimum_sample"] is False, "3 items is far below the 150 floor"


def test_adjudication_is_required_for_every_disagreement(tmp_path):
    a_path, b_path = tmp_path / "a.csv", tmp_path / "b.csv"
    _write(a_path, [{"item_id": "1", "arm": "compositional", "category": "temporal"}])
    _write(b_path, [{"item_id": "1", "arm": "compositional", "category": "numeric_threshold"}])
    a, b = load_annotations(a_path), load_annotations(b_path)
    dis = disagreements(a, b)
    assert len(dis) == 1 and dis[0]["adjudication_rule"] == "resolve_on_merits"

    # Unresolved disagreements must fail loudly: the paper claims all were adjudicated.
    with pytest.raises(ValueError):
        consensus_labels(a, b)

    sheet = tmp_path / "adj.csv"
    write_adjudication_sheet(dis, sheet)
    rows = list(csv.DictReader(open(sheet, encoding="utf-8")))
    rows[0]["resolved_category"] = "temporal"
    with open(sheet, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    consensus = consensus_labels(a, b, load_adjudication(sheet))
    assert consensus == {"1": "temporal"}


def test_clinical_disagreements_route_to_annotator_one(tmp_path):
    a_path, b_path = tmp_path / "a.csv", tmp_path / "b.csv"
    _write(a_path, [{"item_id": "1", "category": "entity_conflation",
                     "clinical_judgement_required": "yes"}])
    _write(b_path, [{"item_id": "1", "category": "implicit_knowledge"}])
    dis = disagreements(load_annotations(a_path), load_annotations(b_path))
    assert dis[0]["adjudication_rule"] == "annotator1_governs"


def test_unknown_category_is_a_hard_error(tmp_path):
    path = tmp_path / "a.csv"
    _write(path, [{"item_id": "1", "category": "logial_compositon"}])  # typo
    with pytest.raises(ValueError):
        load_annotations(path)


def test_blank_categories_are_skipped_not_defaulted(tmp_path):
    path = tmp_path / "a.csv"
    _write(path, [{"item_id": "1", "category": ""}, {"item_id": "2", "category": "temporal"}])
    assert set(load_annotations(path)) == {"2"}


def test_automatic_vs_consensus_counts_impossible_agreements(tmp_path):
    auto = tmp_path / "auto.csv"
    with open(auto, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "automatic_category"])
        w.writeheader()
        w.writerow({"item_id": "1", "automatic_category": "logical_composition"})
        w.writerow({"item_id": "2", "automatic_category": "logical_composition"})
    out = automatic_vs_consensus({"1": "logical_composition", "2": "fabrication"}, auto)
    # fabrication is unreachable for the labeller, so that item can never agree.
    assert out["n"] == 2 and out["n_agreement_impossible"] == 1
    assert out["percent_agreement"] == 0.5
