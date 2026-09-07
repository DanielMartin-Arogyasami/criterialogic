"""Calibration and abstention metrics.

Thin wrappers over :mod:`criterialogic.metrics.stats` that adapt benchmark Items and
Predictions to the ``(confidence, correct)`` rows the statistics work on. The arithmetic
lives in ``stats`` so it can be read and tested without pydantic installed.

The selective-accuracy curve here is tie-aware and reports whether the confidences
were degenerate. That is not a refinement: the v0.1 audit found a constant-confidence
baseline whose reported curve varied by 0.47 purely from list order, presented as a
calibration result. A model that emits one confidence value has no abstention signal,
and the flag says so.
"""
from __future__ import annotations

from criterialogic.metrics.stats import expected_calibration_error as _ece
from criterialogic.metrics.stats import is_degenerate_confidence as _degenerate
from criterialogic.metrics.stats import selective_accuracy as _selective


def _rows(items, predictions) -> list[tuple[float, bool]]:
    pred_by_id = {p.item_id: p for p in predictions}
    return [(pred_by_id[it.item_id].confidence, pred_by_id[it.item_id].label == it.gold)
            for it in items]


def expected_calibration_error(items, predictions, n_bins: int = 10) -> float:
    """ECE: weighted average gap between confidence and accuracy across equal-width bins."""
    return _ece(_rows(items, predictions), n_bins=n_bins)


def selective_accuracy_curve(items, predictions) -> dict:
    """Tie-aware accuracy at 10%..100% coverage, plus a degenerate-confidence flag."""
    return _selective(_rows(items, predictions))


def has_usable_confidence_signal(items, predictions) -> bool:
    """False when every prediction carries the same confidence."""
    return not _degenerate(_rows(items, predictions))
