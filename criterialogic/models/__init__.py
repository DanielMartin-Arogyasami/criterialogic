"""Baseline adapters behind one pluggable Model interface.

One interface is the main lever for outside adoption: a submission implements
``predict(item) -> Prediction`` and nothing else. The encoder and local-LLM stubs that
shipped in v0.1 are gone — they raised NotImplementedError, which is a promise, not a
baseline. See docs/V2_SCOPE.md.
"""
from criterialogic.models.base import Model  # noqa: F401
from criterialogic.models.llm_api import OpenAILLMModel, OpenRouterLLMModel, TogetherLLMModel
from criterialogic.models.naive import NegationBlindModel
from criterialogic.models.rule_based import RuleBasedModel

REGISTRY = {
    "rule_based": RuleBasedModel,
    "negation_blind": NegationBlindModel,
    "openai": OpenAILLMModel,
    "openrouter": OpenRouterLLMModel,
    "together": TogetherLLMModel,
}

#: Chat adapters that take ``prompt_version`` and must reuse the v2 prompt.
LLM_MODELS = ("openai", "openrouter", "together")

#: Models that need no API key or network. Both are diagnostics rather than systems:
#: rule_based evaluates the already-structured form and is therefore the oracle itself,
#: and negation_blind is deliberately broken. Neither belongs on a leaderboard.
OFFLINE_MODELS = ["rule_based", "negation_blind"]
