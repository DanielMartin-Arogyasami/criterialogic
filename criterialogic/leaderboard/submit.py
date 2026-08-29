"""Validate a leaderboard submission file.
A submission is JSON: {"model": "<name>", "task": "<task>",
"predictions": [{"item_id": ..., "label": bool, "confidence": float}, ...]}.
Validation checks the schema and that every evaluated item is covered.
"""
from __future__ import annotations

import json

from criterialogic.tasks.base import Prediction


class SubmissionError(ValueError):
    pass
def load_submission(path: str) -> dict:
    with open(path) as fh:
        data = json.load(fh)
    for key in ("model", "task", "predictions"):
        if key not in data:
            raise SubmissionError(f"Submission missing required field: '{key}'")
    data["predictions"] = [Prediction(**p) for p in data["predictions"]]
    return data
def validate_against_items(submission: dict, items) -> None:
    have = {p.item_id for p in submission["predictions"]}
    need = {it.item_id for it in items}
    missing, extra = need - have, have - need
    if missing:
        raise SubmissionError(f"Submission missing {len(missing)} predictions, e.g. {sorted(missing)[:3]}")
    if extra:
        raise SubmissionError(f"Submission has {len(extra)} unknown item_ids, e.g. {sorted(extra)[:3]}")
