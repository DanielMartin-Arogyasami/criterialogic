"""The single Model interface every baseline / submission implements.
One interface is the biggest lever for leaderboard adoption (spec §8): anyone
can plug in a system by subclassing `Model` and implementing `predict`.
"""
from __future__ import annotations

import abc

from criterialogic.tasks.base import Item, Prediction


class Model(abc.ABC):
    """Predict a met/not-met decision (+ confidence) for a benchmark Item."""
    #: short identifier used in result files / the leaderboard
    name: str = "model"
    @abc.abstractmethod
    def predict(self, item: Item) -> Prediction:
        """Return a Prediction for one Item. Must set item_id, label, confidence."""
    def predict_batch(self, items: list[Item]) -> list[Prediction]:
        return [self.predict(item) for item in items]
    def info(self) -> dict:
        """Reproducibility metadata logged into every result file."""
        return {"name": self.name, "type": type(self).__name__}
