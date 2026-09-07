"""OpenAI adapter: rendering + parsing + graceful failure, with the API call mocked."""
from criterialogic.models.llm_api import (
    PROMPT_VERSION,
    OpenAILLMModel,
    render_expression,
    render_patient,
)
from criterialogic.oracle import Fact, PatientFacts
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Entity,
    EntityType,
    Not,
)
from criterialogic.tasks.compositional import generate_compositional_items


class _Fake(OpenAILLMModel):
    """OpenAI adapter with the network call replaced by a canned response (or exception)."""
    def __init__(self, canned, **kw):
        super().__init__(cache_dir=None, **kw)  # no disk cache in tests
        self._canned = canned
    def _complete(self, system, user):
        if isinstance(self._canned, Exception):
            raise self._canned
        return self._canned
def _an_item():
    return generate_compositional_items(n_per_depth=1, max_depth=1, seed=1)[0]
def test_parses_clean_json():
    m = _Fake('{"label": true, "confidence": 0.9, "rationale": "meets"}')
    p = m.predict(_an_item())
    assert p.label is True and abs(p.confidence - 0.9) < 1e-9 and p.rationale == "meets"
def test_strips_code_fence_and_clamps_confidence():
    m = _Fake('```json\n{"label": false, "confidence": 1.5}\n```')
    p = m.predict(_an_item())
    assert p.label is False and p.confidence == 1.0  # clamped into [0,1]
def test_graceful_failure_abstains():
    m = _Fake(RuntimeError("boom"), max_retries=0)
    p = m.predict(_an_item())
    assert p.abstain is True and p.confidence == 0.0 and "boom" in p.rationale
def test_render_expression_is_faithful():
    a = Atom(entity=Entity(text="t2dm", type=EntityType.CONDITION))
    b = Atom(entity=Entity(text="aspirin", type=EntityType.DRUG))
    expr = BooleanGroup(operator=BoolOp.AND, operands=[a, Not(operand=b)])
    s = render_expression(expr)
    assert "AND" in s and "NOT" in s and "t2dm" in s and "aspirin" in s
def test_info_reports_model():
    m = _Fake("{}", model="gpt-4o-mini")
    assert m.info()["provider"] == "openai" and m.info()["model"] == "gpt-4o-mini"
import types  # noqa: E402


def test_string_and_numeric_label_coercion():
    assert _Fake('{"label": "false", "confidence": 0.8}').predict(_an_item()).label is False
    assert _Fake('{"label": "met", "confidence": 0.8}').predict(_an_item()).label is True
    assert _Fake('{"label": 1, "confidence": 0.8}').predict(_an_item()).label is True
    # an uninterpretable label must abstain, not silently guess
    assert _Fake('{"label": "maybe", "confidence": 0.8}').predict(_an_item()).abstain is True
class _TempRejectingClient:
    """Fake OpenAI client: rejects a custom temperature, succeeds without one."""
    def __init__(self):
        self.n_calls = 0
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create))
    def _create(self, **kwargs):
        self.n_calls += 1
        if "temperature" in kwargs:
            raise RuntimeError("Unsupported value: 'temperature' is not supported with this model.")
        msg = types.SimpleNamespace(content='{"label": true, "confidence": 0.6}')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
def test_temperature_rejection_fallback():
    c = _TempRejectingClient()
    m = OpenAILLMModel(client=c, cache_dir=None, max_retries=0)
    p = m.predict(_an_item())
    assert p.abstain is False and p.label is True          # succeeded via fallback
    assert m.temperature is None and c.n_calls == 2        # retried once without temperature


def test_predict_batch_is_order_preserving_under_concurrency():
    """Concurrency is a latency optimization only; it must not permute or drop results."""
    items = generate_compositional_items(n_per_depth=2, max_depth=1, seed=7)

    class _PerItem(OpenAILLMModel):
        def __init__(self, **kw):
            super().__init__(cache_dir=None, **kw)

        def predict(self, item):
            from criterialogic.tasks.base import Prediction
            return Prediction(item_id=item.item_id, label=True, confidence=0.5)

    serial = _PerItem(concurrency=1).predict_batch(items)
    parallel = _PerItem(concurrency=8).predict_batch(items)
    assert [p.item_id for p in serial] == [i.item_id for i in items]
    assert [p.item_id for p in parallel] == [i.item_id for i in items]


# --------------------------------------------------------------------------- #
# Prompt renderer versioning — the currency-rendering defect and its fix
# --------------------------------------------------------------------------- #
def test_renderer_v1_omits_currency_and_v2_states_it():
    facts = PatientFacts(record_id="r", facts={"aspirin": Fact(present=True, current=False)})
    v1 = render_patient(facts, prompt_version="1")
    v2 = render_patient(facts, prompt_version="2")
    # v1 renders a present-but-not-current fact identically to one whose currency was
    # never recorded, which is what made those gold labels unanswerable from the prompt.
    assert "current" not in v1.lower()
    assert "not currently active" in v2
    assert PROMPT_VERSION == "2", "v2 is the default; v1 exists to reproduce v0.2 numbers"


def test_unknown_prompt_version_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        render_patient(PatientFacts(record_id="r", facts={}), prompt_version="99")
    with pytest.raises(ValueError):
        OpenAILLMModel(cache_dir=None, prompt_version="99")


def test_cache_key_separates_prompt_versions():
    """Two renderer versions must never share a cache entry."""
    a = OpenAILLMModel(cache_dir=None, prompt_version="1", client=object())
    b = OpenAILLMModel(cache_dir=None, prompt_version="2", client=object())
    assert a._cache_key("sys", "user") != b._cache_key("sys", "user")


def test_dropped_parameters_are_recorded_not_silently_forgotten():
    class _Rejects:
        class chat:
            class completions:
                calls = []

                @staticmethod
                def create(**kw):
                    _Rejects.chat.completions.calls.append(kw)
                    if "temperature" in kw:
                        raise RuntimeError("Unsupported value: 'temperature' is not supported")

                    class R:
                        choices = [type("C", (), {"message": type(
                            "M", (), {"content": '{"label": true, "confidence": 0.7}'})()})()]
                    return R()

    m = OpenAILLMModel(client=_Rejects(), cache_dir=None, max_retries=0)
    m.predict(_an_item())
    info = m.info()
    assert info["requested_temperature"] == 0.0
    assert info["effective_temperature"] == "api_default"
    assert info["dropped_parameters"] == ["temperature"], (
        "a result file must not assert a parameter the API refused")


def test_openrouter_and_together_reuse_the_openai_prompt():
    """A second system is only comparable if it sees the same prompt."""
    from criterialogic.models import LLM_MODELS, REGISTRY
    from criterialogic.models.llm_api import (
        OpenRouterLLMModel,
        TogetherLLMModel,
        system_prompt,
    )

    assert set(LLM_MODELS) <= set(REGISTRY)
    item = _an_item()
    openai = OpenAILLMModel(cache_dir=None, client=object())
    for cls in (OpenRouterLLMModel, TogetherLLMModel):
        other = cls(cache_dir=None, client=object())
        assert other._build_prompt(item) == openai._build_prompt(item)
        assert system_prompt(other.prompt_version) == system_prompt(openai.prompt_version)
        info = other.info()
        assert info["provider"] == other.provider
        assert "effective_temperature" in info
        assert "dropped_parameters" in info
