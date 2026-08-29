"""Open-weight LLM baseline (Llama / Mistral / Qwen via HF or vLLM) — interface stub.
Same contract as ApiLLMModel; the body is a TODO requiring a local runtime.
Import-safe so the demo runs without a GPU stack.
"""
from __future__ import annotations

from criterialogic.models.base import Model
from criterialogic.tasks.base import Item, Prediction


class LocalLLMModel(Model):
    name = "llm_local"
    def __init__(self, model: str = "meta-llama/Llama-3.1-8B-Instruct", backend: str = "hf"):
        self.model = model
        self.backend = backend
    def predict(self, item: Item) -> Prediction:  # pragma: no cover
        raise NotImplementedError(
            "LocalLLMModel requires a HF/vLLM runtime. Load `model`, prompt it on the "
            "criterion + note, parse {label, confidence}. See models/llm_local.py."
        )
