"""Orchestrates one evaluation: model over a task's items, metrics, diagnostics, provenance.

Every result file this writes is meant to be auditable without rerunning anything, which
means it carries three things v0.1 result files did not:

* **Per-item predictions.** ``per_item_predictions`` records item_id, depth, gold,
  predicted, confidence and correctness for every item. The v0.1 audit could not
  recompute a corrected selective-accuracy curve because only aggregates were stored, so
  it had to detect the problem algebraically instead of just fixing it.
* **Effective, not requested, parameters.** ``model`` is whatever ``Model.info()``
  reports, and the LLM adapter reports the parameters the API actually applied plus any
  it dropped. A run record asserting temperature=0 when the model refused it is a
  reproducibility claim the artifact cannot support.
* **Component versions.** Schema, prompt renderer, and heuristic-labeller versions, so a
  number can always be attributed to the code that produced it.
"""
from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone

from criterialogic.metrics.calibration import (
    expected_calibration_error,
    has_usable_confidence_signal,
    selective_accuracy_curve,
)
from criterialogic.metrics.classification import accuracy
from criterialogic.metrics.decision import decision_scores
from criterialogic.metrics.logic import accuracy_by_depth
from criterialogic.schema.logical_form import SCHEMA_VERSION
from criterialogic.taxonomy.annotate import LABELLER_VERSION, failure_breakdown, is_unanswerable


def _provenance(items, prompt_version: str | None = "1") -> dict:
    """What the item set is made of, read off the items rather than asserted."""
    first = items[0]
    meta = first.criterion.metadata
    sources = sorted({it.criterion.source.value for it in items})
    polarities = sorted({it.criterion.polarity.value for it in items})
    prov = {
        "sources": sources,
        "polarities": polarities,
        "patients": "synthetic",
        "composition": meta.get("composition", "real"),
        "n_unanswerable_items": sum(1 for it in items
                                    if is_unanswerable(it, prompt_version)),
    }
    for key in ("atom_pool_sha256", "atom_source", "snapshot_id", "generator_seed",
                "generator_depths"):
        if meta.get(key):
            prov[key] = meta[key]
    return prov


def run_task(model, items, seed: int | None = None) -> dict:
    """Evaluate ``model`` on ``items`` (one task). Returns a serialisable result dict."""
    if not items:
        raise ValueError("No items to evaluate.")
    task = items[0].task
    predictions = model.predict_batch(items)
    # Answerability depends on which renderer the model saw, so read it off the model
    # rather than assuming. None = no prompt involved (the offline diagnostics).
    prompt_version = model.info().get("prompt_version")
    pred_by_id = {p.item_id: p for p in predictions}

    result: dict = {
        "task": task,
        "model": model.info(),
        "n_items": len(items),
        "provenance": _provenance(items, prompt_version),
        "metrics": {},
        "failure_taxonomy": failure_breakdown(items, predictions,
                                              prompt_version=prompt_version),
        "calibration": {
            "ece": expected_calibration_error(items, predictions),
            "mean_confidence": round(
                sum(p.confidence for p in predictions) / len(predictions), 4),
            "n_abstain": sum(1 for p in predictions if p.abstain),
            "usable_confidence_signal": has_usable_confidence_signal(items, predictions),
            "selective_accuracy": selective_accuracy_curve(items, predictions),
        },
        "per_item_predictions": [
            {
                "item_id": it.item_id,
                "depth": it.depth,
                "group": it.group,
                "gold": "met" if it.gold else "not_met",
                "predicted": "met" if pred_by_id[it.item_id].label else "not_met",
                "confidence": pred_by_id[it.item_id].confidence,
                "abstain": pred_by_id[it.item_id].abstain,
                "correct": pred_by_id[it.item_id].label == it.gold,
                "unanswerable": is_unanswerable(it, prompt_version),
                # Persisted because the annotation export reads it: docs/CODEBOOK.md
                # instructs annotators to read the model's stated reasoning, and
                # fabrication (category 7) can only be identified from it.
                "rationale": pred_by_id[it.item_id].rationale,
            }
            for it in items
        ],
        "versions": {
            "schema": SCHEMA_VERSION,
            "failure_labeller": LABELLER_VERSION,
            "prompt_renderer": model.info().get("prompt_version"),
        },
        "repro": {
            "seed": seed,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }

    if task == "compositional":
        result["metrics"] = accuracy_by_depth(items, predictions)
    elif task in ("real_criteria", "matching"):
        result["metrics"] = decision_scores(items, predictions)
    else:
        result["metrics"] = {
            "accuracy": accuracy([it.gold for it in items],
                                 [pred_by_id[it.item_id].label for it in items])
        }
    return result
