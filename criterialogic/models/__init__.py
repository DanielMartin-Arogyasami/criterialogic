"""Baseline adapters behind one pluggable Model interface (the adoption lever)."""
from criterialogic.models.base import Model  # noqa: F401
from criterialogic.models.llm_api import OpenAILLMModel
from criterialogic.models.naive import NegationBlindModel
from criterialogic.models.rule_based import RuleBasedModel

REGISTRY = {
    "rule_based": RuleBasedModel,
    "negation_blind": NegationBlindModel,
    "openai": OpenAILLMModel,
}
# Models that need no API key / network — used as the default demo sweep.
OFFLINE_MODELS = ["rule_based", "negation_blind"]
