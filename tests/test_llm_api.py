"""OpenAI adapter: rendering + parsing + graceful failure, with the API call mocked."""
from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.models.llm_api import OpenAILLMModel, render_expression
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Entity,
    EntityType,
    Not,
)


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
    return generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=1, seed=1)[0]
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
    items = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=2, seed=7)

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
