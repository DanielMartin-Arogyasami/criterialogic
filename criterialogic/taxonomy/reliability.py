"""Reliability tooling for the reasoning-failure taxonomy (single-annotator workflow).
Operationalizes the paper's Section 5 procedure without a second annotator:
1. `export_error_set(items, predictions, path)` writes every misclassified item to a CSV
   with the rendered criterion, the patient facts, gold vs predicted, the automatic
   heuristic category, and a blank `human_category` column for the annotator to fill.
2. The domain-expert annotator fills `human_category` (in a spreadsheet), using the codebook.
3. `reliability_report(...)` computes:
     - human vs. automatic agreement (Cohen's κ + percent) — the independent cross-check;
     - test–retest agreement between two annotation passes — intra-annotator reliability.
All metrics are implemented from scratch (stdlib only).
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from criterialogic.models.llm_api import render_criterion, render_patient
from criterialogic.taxonomy.annotate import categorize_error
from criterialogic.taxonomy.categories import FailureCategory

CATEGORY_VALUES = [c.value for c in FailureCategory]
def cohens_kappa(a: list[str], b: list[str]) -> float:
    """Cohen's κ between two aligned lists of categorical labels."""
    if len(a) != len(b):
        raise ValueError("label lists must be the same length")
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    cats = set(a) | set(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if pe >= 1.0:  # both raters used a single identical category throughout
        return 1.0
    return (po - pe) / (1 - pe)
def percent_agreement(a: list[str], b: list[str]) -> float:
    if len(a) != len(b):
        raise ValueError("label lists must be the same length")
    return sum(1 for x, y in zip(a, b) if x == y) / len(a) if a else 0.0
def _error_rows(items, predictions):
    pred = {p.item_id: p for p in predictions}
    for it in items:
        p = pred[it.item_id]
        if p.label != it.gold:  # errors only
            yield it, p, categorize_error(it, p).value
def export_error_set(items, predictions, path: str) -> dict:
    """Write the error set to a CSV for human annotation. Returns a small summary."""
    rows = list(_error_rows(items, predictions))
    fields = ["item_id", "task", "criterion", "patient_facts", "gold", "predicted",
              "confidence", "automatic_category", "human_category"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for it, p, auto in rows:
            w.writerow({
                "item_id": it.item_id,
                "task": it.task,
                "criterion": render_criterion(it.criterion),
                "patient_facts": render_patient(it.facts).replace("\n", " | "),
                "gold": "met" if it.gold else "not_met",
                "predicted": "met" if p.label else "not_met",
                "confidence": f"{p.confidence:.3f}",
                "automatic_category": auto,
                "human_category": "",  # annotator fills this using the codebook
            })
    return {"path": path, "n_errors": len(rows), "categories": CATEGORY_VALUES}
def load_labels(path: str, column: str = "human_category") -> dict[str, str]:
    """Read {item_id: label} from an annotated CSV (skips blank labels)."""
    out: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            val = (row.get(column) or "").strip()
            if val:
                out[row["item_id"]] = val
    return out
def human_vs_automatic(items, predictions, human_labels: dict[str, str]) -> dict:
    """Agreement between the human labels and the automatic heuristic labeler."""
    auto = {it.item_id: cat for it, _, cat in _error_rows(items, predictions)}
    ids = [i for i in human_labels if i in auto]
    h = [human_labels[i] for i in ids]
    a = [auto[i] for i in ids]
    return {
        "n": len(ids),
        "cohens_kappa": round(cohens_kappa(h, a), 4),
        "percent_agreement": round(percent_agreement(h, a), 4),
        "human_distribution": dict(Counter(h)),
        "automatic_distribution": dict(Counter(a)),
    }
def test_retest(labels_pass1: dict[str, str], labels_pass2: dict[str, str]) -> dict:
    """Intra-annotator agreement between two labeling passes over the shared items."""
    ids = [i for i in labels_pass1 if i in labels_pass2]
    a = [labels_pass1[i] for i in ids]
    b = [labels_pass2[i] for i in ids]
    return {
        "n": len(ids),
        "cohens_kappa": round(cohens_kappa(a, b), 4),
        "percent_agreement": round(percent_agreement(a, b), 4),
    }
def reliability_report(items, predictions, human_csv: str, retest_csv: str | None = None) -> dict:
    """Convenience: human-vs-automatic (+ optional test–retest) from annotated CSV(s)."""
    human = load_labels(human_csv)
    report = {"human_vs_automatic": human_vs_automatic(items, predictions, human)}
    if retest_csv:
        report["test_retest"] = test_retest(human, load_labels(retest_csv))
    return report
