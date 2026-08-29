"""Fine-tuned encoder baseline (BioClinicalBERT / PubMedBERT) — interface stub.
Implements the Model contract; the body is a TODO requiring `transformers`,
`torch`, and a fine-tuned checkpoint (Tasks B–C). Kept import-safe so the demo
runs without heavy ML dependencies installed.
"""
from __future__ import annotations

from criterialogic.models.base import Model
from criterialogic.tasks.base import Item, Prediction


class EncoderModel(Model):
    name = "encoder"
    def __init__(self, checkpoint: str = "emilyalsentzer/Bio_ClinicalBERT"):
        self.checkpoint = checkpoint
        # TODO: lazy-load tokenizer + classification head from `checkpoint`.
    def predict(self, item: Item) -> Prediction:  # pragma: no cover
        raise NotImplementedError(
            "EncoderModel requires transformers/torch and a fine-tuned head. "
            "Install the [encoder] extra and load a checkpoint. See models/encoder.py."
        )
