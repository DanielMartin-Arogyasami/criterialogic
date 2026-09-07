"""Leaderboard submission validation + scoring round-trip."""
import json

import pytest

from criterialogic.leaderboard.score import rank, score_submission
from criterialogic.leaderboard.submit import (
    SubmissionError,
    load_submission,
    validate_against_items,
)
from criterialogic.models import RuleBasedModel
from criterialogic.tasks.compositional import generate_compositional_items


def _items():
    return generate_compositional_items(n_per_depth=6, max_depth=2, seed=1)


def _submission(items, drop=0, extra=0):
    preds = RuleBasedModel().predict_batch(items)
    rows = [p.model_dump() for p in preds]
    if drop:
        rows = rows[:-drop]
    for i in range(extra):
        rows.append({"item_id": f"not-an-item-{i}", "label": True, "confidence": 0.5})
    return {"model": "rule_based", "task": "compositional", "predictions": rows}


def test_submission_round_trip(tmp_path):
    items = _items()
    path = tmp_path / "submission.json"
    path.write_text(json.dumps(_submission(items)))
    loaded = load_submission(str(path))
    validate_against_items(loaded, items)  # should not raise
    scored = score_submission(loaded, items)
    # rule_based is the oracle on structured input, so this is 1.0 by construction.
    assert scored["metrics"]["overall_accuracy"] == 1.0
    assert scored["versions"]["schema"]


def test_incomplete_submission_is_rejected(tmp_path):
    items = _items()
    path = tmp_path / "short.json"
    path.write_text(json.dumps(_submission(items, drop=2)))
    with pytest.raises(SubmissionError):
        validate_against_items(load_submission(str(path)), items)


def test_unknown_item_ids_are_rejected(tmp_path):
    """A submission scored against a partly different item set is not comparable."""
    items = _items()
    path = tmp_path / "extra.json"
    path.write_text(json.dumps(_submission(items, extra=1)))
    with pytest.raises(SubmissionError):
        validate_against_items(load_submission(str(path)), items)


def test_missing_required_field(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"model": "x", "predictions": []}))
    with pytest.raises(SubmissionError):
        load_submission(str(path))


def test_rank_uses_the_task_headline_metric():
    a = {"metrics": {"overall_accuracy": 0.6}}
    b = {"metrics": {"overall_accuracy": 0.9}}
    assert rank([a, b], "compositional")[0] is b
