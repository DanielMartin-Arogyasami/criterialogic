"""Validate a leaderboard submission file.

A submission is JSON::

    {"model": "<name>", "task": "<task>",
     "predictions": [{"item_id": ..., "label": bool, "confidence": float}, ...]}

Everything here treats the file as untrusted input from a third party, because that is
what a leaderboard submission is. Every failure mode surfaces as ``SubmissionError`` with
a message naming the offending row, rather than as a pydantic traceback or a KeyError
raised later inside the scorer.
"""
from __future__ import annotations

import json

from criterialogic.tasks.base import Prediction

#: A submission file large enough to be a mistake or an attack rather than a submission.
#: The largest legitimate item set in the benchmark is a few thousand predictions.
MAX_SUBMISSION_BYTES = 64 * 1024 * 1024
MAX_PREDICTIONS = 1_000_000


class SubmissionError(ValueError):
    pass


def load_submission(path: str) -> dict:
    """Parse and structurally validate a submission file."""
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read(MAX_SUBMISSION_BYTES + 1)
    except OSError as e:
        raise SubmissionError(f"Could not read submission {path!r}: {e}") from e
    if len(raw) > MAX_SUBMISSION_BYTES:
        raise SubmissionError(
            f"Submission {path!r} exceeds {MAX_SUBMISSION_BYTES} bytes and was not parsed."
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SubmissionError(f"Submission {path!r} is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise SubmissionError(f"Submission {path!r} must be a JSON object, got {type(data).__name__}.")

    for key in ("model", "task", "predictions"):
        if key not in data:
            raise SubmissionError(f"Submission missing required field: '{key}'")
    if not isinstance(data["model"], str) or not data["model"].strip():
        raise SubmissionError("Field 'model' must be a non-empty string.")
    if not isinstance(data["task"], str) or not data["task"].strip():
        raise SubmissionError("Field 'task' must be a non-empty string.")
    rows = data["predictions"]
    if not isinstance(rows, list):
        raise SubmissionError(f"Field 'predictions' must be a list, got {type(rows).__name__}.")
    if not rows:
        raise SubmissionError("Field 'predictions' is empty.")
    if len(rows) > MAX_PREDICTIONS:
        raise SubmissionError(f"Submission has {len(rows)} predictions; the cap is {MAX_PREDICTIONS}.")

    parsed: list[Prediction] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SubmissionError(f"predictions[{i}] must be an object, got {type(row).__name__}.")
        try:
            parsed.append(Prediction(**row))
        except Exception as e:
            # Includes pydantic ValidationError (confidence out of [0, 1], missing
            # item_id, wrong types) and TypeError from unexpected keys.
            raise SubmissionError(f"predictions[{i}] is invalid: {e}") from e

    ids = [p.item_id for p in parsed]
    duplicates = {i for i in ids if ids.count(i) > 1} if len(set(ids)) != len(ids) else set()
    if duplicates:
        raise SubmissionError(
            f"Submission contains {len(duplicates)} duplicate item_id(s), e.g. "
            f"{sorted(duplicates)[:3]}. Two predictions for one item make the score "
            f"depend on which one is read."
        )
    data["predictions"] = parsed
    return data


def validate_against_items(submission: dict, items) -> None:
    """Require exact coverage of the evaluated items — no gaps, no extras."""
    have = {p.item_id for p in submission["predictions"]}
    need = {it.item_id for it in items}
    missing, extra = need - have, have - need
    if missing:
        raise SubmissionError(
            f"Submission missing {len(missing)} predictions, e.g. {sorted(missing)[:3]}"
        )
    if extra:
        raise SubmissionError(
            f"Submission has {len(extra)} unknown item_ids, e.g. {sorted(extra)[:3]}"
        )
