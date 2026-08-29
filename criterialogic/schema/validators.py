"""Corpus-level validation (beyond the intrinsic per-model checks in logical_form).
These run over a *collection* of LogicalForm records, e.g. after harmonization,
to catch problems the single-record pydantic validators cannot see: duplicate
ids, schema-version drift, and (for split hygiene) trial-id leakage.
"""
from __future__ import annotations

from collections import Counter

from criterialogic.schema.logical_form import SCHEMA_VERSION, LogicalForm


class CorpusValidationError(ValueError):
    """Raised when a collection of LogicalForm records is internally inconsistent."""
def check_unique_ids(forms: list[LogicalForm]) -> None:
    """Every ``criterion_id`` must be unique across the corpus."""
    dupes = [cid for cid, n in Counter(f.criterion_id for f in forms).items() if n > 1]
    if dupes:
        raise CorpusValidationError(f"Duplicate criterion_id(s): {sorted(dupes)}")
def check_schema_version(forms: list[LogicalForm], expected: str = SCHEMA_VERSION) -> None:
    """All records should share one schema version (no silent format drift)."""
    bad = {f.schema_version for f in forms if f.schema_version != expected}
    if bad:
        raise CorpusValidationError(f"Mixed schema versions present: {sorted(bad)} (expected {expected}).")
def check_no_trial_leakage(train: list[LogicalForm], test: list[LogicalForm], key: str = "trial_id") -> None:
    """No trial id may appear in both splits (prevents train/test contamination)."""
    tr = {f.metadata.get(key) for f in train if f.metadata.get(key)}
    te = {f.metadata.get(key) for f in test if f.metadata.get(key)}
    overlap = tr & te
    if overlap:
        raise CorpusValidationError(f"Trial-id leakage across splits: {sorted(overlap)}")
def validate_corpus(forms: list[LogicalForm], expected_version: str = SCHEMA_VERSION) -> None:
    """Run all single-corpus checks; raises on the first failure."""
    check_unique_ids(forms)
    check_schema_version(forms, expected_version)
