"""OpenAI LLM baseline for CriteriaLogic.
Renders each item's criterion (its logical structure) and the patient's facts into a
prompt, asks an OpenAI chat model for a met/not-met decision plus a calibrated
confidence, and returns a Prediction. Designed for real benchmark runs:
* JSON-mode output + robust parsing (survives stray prose / code fences).
* temperature=0 by default for reproducibility; auto-dropped for models that reject it.
* On-disk response cache keyed by (model, prompt) so re-runs are free and resumable.
* Retries on transient/rate-limit errors, and per-item graceful failure (a single bad
  call yields a low-confidence abstain rather than aborting the whole evaluation).
Setup:  pip install -e ".[llm]"  and  export OPENAI_API_KEY=...
Choose the model with the CRITERIALOGIC_LLM_MODEL env var (default: gpt-4o-mini) or the
`model=` constructor argument. Run e.g.:  python scripts/run_eval.py --task compositional --model openai
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from criterialogic.models.base import Model
from criterialogic.oracle import PatientFacts
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Expression,
    LogicalForm,
    Not,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
)
from criterialogic.tasks.base import Item, Prediction

DEFAULT_MODEL = os.environ.get("CRITERIALOGIC_LLM_MODEL", "gpt-4o-mini")
_SYSTEM = (
    "You are a careful clinical-trial eligibility assessor. You are given one eligibility "
    "CRITERION (which may nest AND / OR / NOT, temporal windows, and numeric thresholds) and a "
    "PATIENT described by a set of facts. Decide whether the patient SATISFIES the criterion. "
    "Reason about the logical structure exactly: respect negation and polarity, AND vs OR, "
    "temporal windows, and numeric boundaries. Any entity not listed for the patient is undocumented; "
    "if the criterion's truth cannot be determined from the facts, choose the value the criterion "
    "implies for an undocumented finding (usually not satisfied) and lower your confidence. "
    'Respond with ONLY a JSON object: {"label": <true|false>, "confidence": <0.0-1.0>, '
    '"rationale": "<one sentence>"}. label=true means the criterion IS satisfied. confidence is your '
    "calibrated probability that the label is correct."
)
_NUM_SYM = {
    Comparator.LT: "< {v}", Comparator.LE: "<= {v}", Comparator.GT: "> {v}",
    Comparator.GE: ">= {v}", Comparator.EQ: "= {v}", Comparator.NE: "!= {v}",
}
# --------------------------------------------------------------------------- #
# Rendering criterion + patient into readable prompt text
# --------------------------------------------------------------------------- #
def _render_numeric(nc: NumericConstraint) -> str:
    unit = f" {nc.unit}" if nc.unit else ""
    if nc.operator is Comparator.BETWEEN:
        return f"between {nc.value} and {nc.upper}{unit}"
    return _NUM_SYM[nc.operator].format(v=nc.value) + unit
def _render_temporal(tc: TemporalConstraint) -> str:
    if tc.operator is TemporalOp.CURRENT:
        return "current / ongoing"
    if tc.operator is TemporalOp.ANY_HISTORY:
        return "at any time in history"
    unit = tc.unit.value if tc.unit else ""
    if tc.operator is TemporalOp.WITHIN:
        return f"within the past {tc.value} {unit}"
    if tc.operator is TemporalOp.BEFORE:
        return f"before enrollment by {tc.value} {unit}"
    if tc.operator is TemporalOp.AFTER:
        return f"after enrollment by {tc.value} {unit}"
    if tc.operator is TemporalOp.FOR_AT_LEAST:
        return f"for at least {tc.value} {unit}"
    if tc.operator is TemporalOp.FOR_AT_MOST:
        return f"for at most {tc.value} {unit}"
    return tc.operator.value
def _render_atom(a: Atom) -> str:
    s = a.entity.text
    if a.numeric is not None:
        s += " " + _render_numeric(a.numeric)
    if a.temporal is not None:
        s += f" ({_render_temporal(a.temporal)})"
    return s
def render_expression(e: Expression) -> str:
    """Faithfully render a logical expression as a readable, parenthesized criterion."""
    if isinstance(e, Atom):
        return _render_atom(e)
    if isinstance(e, Not):
        return f"NOT ({render_expression(e.operand)})"
    if isinstance(e, BooleanGroup):
        joiner = " AND " if e.operator is BoolOp.AND else " OR "
        return "(" + joiner.join(render_expression(op) for op in e.operands) + ")"
    raise TypeError(type(e))
def render_criterion(form: LogicalForm) -> str:
    logic = render_expression(form.expression)
    text = (form.text or "").strip()
    polarity = form.polarity.value
    if text and not text.startswith("("):  # real criterion text present (n2c2); show both
        return f'"{text}"\nLogical form ({polarity} criterion): {logic}'
    return f"({polarity} criterion) {logic}"
def render_patient(facts: PatientFacts) -> str:
    if not facts.facts:
        return "No findings are documented for this patient."
    lines = []
    for name, f in facts.facts.items():
        if not f.present:
            lines.append(f"- {name}: absent / negative")
            continue
        bits = ["present"]
        if f.value is not None:
            bits.append(f"value = {f.value}")
        if f.current:
            bits.append("currently active")
        if f.days_ago is not None:
            bits.append(f"most recent occurrence ~{f.days_ago:g} days ago")
        lines.append(f"- {name}: " + ", ".join(bits))
    return "\n".join(lines)
def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):  # strip accidental code fences
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {raw[:200]!r}")
    return json.loads(raw[start : end + 1])
def _clamp(x, lo=0.0, hi=1.0) -> float:
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return 0.5
_TRUE = {"true", "yes", "met", "meets", "satisfied", "1"}
_FALSE = {"false", "no", "not met", "not_met", "unmet", "does not meet", "0"}
def _to_bool(v) -> bool:
    """Coerce a model's label to bool robustly (JSON bool, 0/1, or a string like "false")."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        t = v.strip().lower()
        if t in _TRUE:
            return True
        if t in _FALSE:
            return False
    raise ValueError(f"uninterpretable label: {v!r}")
class OpenAILLMModel(Model):
    name = "openai"
    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = 0.0,
        cache_dir: str | None = ".criterialogic_cache",
        max_retries: int = 4,
        client=None,
    ):
        self.model = model or DEFAULT_MODEL
        self.temperature = temperature
        self.max_retries = max_retries
        self._client = client
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
    def info(self) -> dict:
        return {"name": self.name, "provider": "openai", "model": self.model,
                "temperature": self.temperature}
    # --- API plumbing (monkeypatchable in tests) --------------------------- #
    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # lazy: no key/package needed to import this module
            self._client = OpenAI(max_retries=self.max_retries)
        return self._client
    def _complete(self, system: str, user: str) -> str:
        def _call(include_temp: bool):
            kwargs = dict(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                response_format={"type": "json_object"},
            )
            if include_temp and self.temperature is not None:
                kwargs["temperature"] = self.temperature
            return self._get_client().chat.completions.create(**kwargs)
        try:
            resp = _call(include_temp=True)
        except Exception as e:
            # Some reasoning models reject a custom temperature; drop it and stop sending it,
            # rather than failing (which would otherwise abstain on every item).
            if self.temperature is not None and "temperature" in str(e).lower():
                self.temperature = None
                resp = _call(include_temp=False)
            else:
                raise
        return resp.choices[0].message.content or ""
    def _cached_complete(self, system: str, user: str) -> str:
        if not self._cache_dir:
            return self._retry_complete(system, user)
        key = hashlib.sha256(f"{self.model}\x00{system}\x00{user}".encode()).hexdigest()
        cpath = self._cache_dir / f"{key}.json"
        if cpath.exists():
            return json.loads(cpath.read_text())["response"]
        out = self._retry_complete(system, user)
        cpath.write_text(json.dumps({"model": self.model, "response": out}))
        return out
    def _retry_complete(self, system: str, user: str) -> str:
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            try:
                return self._complete(system, user)
            except Exception:
                if attempt == self.max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")
    def _build_prompt(self, item: Item) -> tuple[str, str]:
        user = (
            f"CRITERION:\n{render_criterion(item.criterion)}\n\n"
            f"PATIENT FACTS (entities not listed are undocumented):\n{render_patient(item.facts)}\n\n"
            "Does the patient satisfy the criterion?"
        )
        return _SYSTEM, user
    def predict(self, item: Item) -> Prediction:
        system, user = self._build_prompt(item)
        try:
            data = _parse_json(self._cached_complete(system, user))
            return Prediction(
                item_id=item.item_id,
                label=_to_bool(data["label"]),
                confidence=_clamp(data.get("confidence", 0.5)),
                rationale=(data.get("rationale") or None),
            )
        except Exception as e:  # per-item graceful failure -> abstain, don't crash the run
            return Prediction(item_id=item.item_id, label=False, confidence=0.0,
                              abstain=True, rationale=f"api/parse error: {type(e).__name__}: {e}")
# Backwards-compatible alias for the previous stub name.
ApiLLMModel = OpenAILLMModel
