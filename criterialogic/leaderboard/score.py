"""Score validated submissions with the benchmark task metrics and rank them."""
from __future__ import annotations

from criterialogic.eval.runner import run_task
from criterialogic.leaderboard.submit import validate_against_items
from criterialogic.models.base import Model
from criterialogic.tasks.base import Item, Prediction


class _ReplayModel(Model):
    """Wrap a submission's predictions as a Model so it flows through the standard runner."""
    def __init__(self, name: str, predictions: list[Prediction]):
        self.name = name
        self._by_id = {p.item_id: p for p in predictions}
    def predict(self, item: Item) -> Prediction:
        return self._by_id[item.item_id]
def score_submission(submission: dict, items: list[Item]) -> dict:
    """Score a submission through the same runner the reported results used.

    Coverage is re-validated here even though callers are expected to have called
    ``validate_against_items`` first. Without it, a submission missing one item raises a
    bare ``KeyError`` from deep inside the runner, which reads as a toolkit bug rather
    than as a rejected submission.
    """
    validate_against_items(submission, items)
    model = _ReplayModel(submission["model"], submission["predictions"])
    return run_task(model, items)
def rank(results: list[dict], task: str) -> list[dict]:
    """Rank result dicts by the task's headline metric (desc).

    Ranking is presentational. The leaderboard table in the README carries the interval
    alongside the point estimate, because at these sample sizes adjacent rows are
    routinely indistinguishable and an ordering alone implies otherwise.
    """
    def key(r):
        m = r["metrics"]
        if task in ("real_criteria", "matching"):
            return m.get("overall_micro_f1", 0.0)
        if task == "compositional":
            return m.get("overall_accuracy", 0.0)
        return m.get("accuracy", 0.0)
    return sorted(results, key=key, reverse=True)
