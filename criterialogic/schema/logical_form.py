"""logical_form.py — CriteriaLogic canonical logical form.

A source-agnostic representation of a single clinical-trial eligibility criterion.
Both benchmark arms operate on this one schema:

* **Arm 1 — real criteria.** Criteria segmented from a dated ClinicalTrials.gov API v2
  snapshot and mapped onto the form by :mod:`criterialogic.data.real_criteria`.
* **Arm 2 — compositional stress test.** Nested AND/OR/NOT expressions of controlled
  depth, composed from atoms extracted from the same snapshot.

Design goals
------------
- **Expressive:** nested AND/OR/NOT scoping plus the three constraint types the
  benchmark targets (entity, temporal, numeric) and criterion-level polarity.
- **Canonical:** one normal form per logic (`canonicalize`: operand sorting,
  same-operator flattening, double-negation collapse, dedupe). Retained for
  deduplication and for the deferred structuring task (see docs/V2_SCOPE.md).
- **Round-trippable:** pure pydantic v2 — `model_dump_json()` /
  `model_validate_json()` reconstruct an identical object.
- **Lossless to source:** criterion-level inclusion/exclusion polarity is kept as a
  label and is *not* folded into the logical expression (see TRADEOFFS in the paper).

Public-domain and synthetic data only. Intrinsic structural validation lives here on
the models; corpus-level checks (cross-criterion, leakage) belong in `validators.py`.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "0.1.0"
# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class Polarity(str, Enum):
    """Which list the criterion was drawn from. Distinct from logical NOT."""
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
class Source(str, Enum):
    """Provenance. Every released record comes from the public-domain snapshot or is
    synthetic; there is no licence-restricted component in v0.2.

    ``CTGOV`` marks a criterion or atom taken from verbatim ClinicalTrials.gov
    eligibility text. ``SYNTHETIC_EXAMPLE`` marks hand-written illustrations used in
    docstrings and tests, which are never part of an evaluated set.
    """
    CTGOV = "ctgov"
    SYNTHETIC_EXAMPLE = "synthetic_example"
class EntityType(str, Enum):
    """Coarse clinical concept type. Deliberately coarse: the benchmark tests logical
    structure, and a fine-grained ontology would add mapping decisions without adding
    anything the tasks measure."""
    CONDITION = "condition"
    DRUG = "drug"
    PROCEDURE = "procedure"
    MEASUREMENT = "measurement"  # lab/vital carrying a numeric value (HbA1c, creatinine)
    OBSERVATION = "observation"
    PERSON = "person"  # demographics (age, sex)
    DEVICE = "device"
    VISIT = "visit"
    LIFESTYLE = "lifestyle"
    OTHER = "other"
class BoolOp(str, Enum):
    AND = "and"
    OR = "or"
class TemporalOp(str, Enum):
    """Temporal relation between the predicate and a reference anchor."""
    WITHIN = "within"  # occurred within `value` `unit` of the anchor (lookback window)
    BEFORE = "before"
    AFTER = "after"
    FOR_AT_LEAST = "for_at_least"  # state has persisted >= duration
    FOR_AT_MOST = "for_at_most"
    CURRENT = "current"  # ongoing/active at the anchor (no magnitude)
    ANY_HISTORY = "any_history"  # ever, unbounded (no magnitude)
class TimeUnit(str, Enum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"
class Comparator(str, Enum):
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    EQ = "eq"
    NE = "ne"
    BETWEEN = "between"
_WINDOWED_TEMPORAL = {
    TemporalOp.WITHIN,
    TemporalOp.BEFORE,
    TemporalOp.AFTER,
    TemporalOp.FOR_AT_LEAST,
    TemporalOp.FOR_AT_MOST,
}
_BARE_TEMPORAL = {TemporalOp.CURRENT, TemporalOp.ANY_HISTORY}
_NUMERIC_ENTITY_TYPES = {
    EntityType.MEASUREMENT,
    EntityType.OBSERVATION,
    EntityType.PERSON,
}
# --------------------------------------------------------------------------- #
# Leaf payloads
# --------------------------------------------------------------------------- #
class Entity(BaseModel):
    """A single clinical concept — the noun a predicate is about."""
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., description="Surface form as annotated in the source.")
    type: EntityType = EntityType.OTHER
    codes: dict[str, str] = Field(
        default_factory=dict,
        description="Optional ontology codes, e.g. {'UMLS': 'C0011860'}. One code per system.",
    )
    @field_validator("text")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Entity.text must be non-empty.")
        return v
class TemporalConstraint(BaseModel):
    """A time qualifier on a predicate, e.g. 'within 6 months of enrollment'."""
    model_config = ConfigDict(extra="forbid")
    operator: TemporalOp
    value: float | None = Field(default=None, description="Magnitude for windowed operators.")
    unit: TimeUnit | None = None
    anchor: str = Field(default="enrollment", description="Reference event the window is measured from.")
    @model_validator(mode="after")
    def _check_magnitude(self) -> TemporalConstraint:
        if self.operator in _WINDOWED_TEMPORAL:
            if self.value is None or self.unit is None:
                raise ValueError(f"Temporal operator '{self.operator.value}' requires value and unit.")
            if self.value <= 0:
                raise ValueError("Temporal value must be positive.")
        if self.operator in _BARE_TEMPORAL and (self.value is not None or self.unit is not None):
            raise ValueError(f"Temporal operator '{self.operator.value}' must not carry value/unit.")
        return self
class NumericConstraint(BaseModel):
    """A numeric threshold on a measurement, e.g. 'HbA1c between 6.5 and 9.5 %'."""
    model_config = ConfigDict(extra="forbid")
    operator: Comparator
    value: float = Field(..., description="The bound; the LOWER bound when operator == BETWEEN.")
    upper: float | None = Field(default=None, description="Upper bound; required iff BETWEEN.")
    unit: str | None = Field(default=None, description="e.g. '%', 'mg/dL', 'years', 'kg/m^2'.")
    lower_inclusive: bool = True
    upper_inclusive: bool = True
    @model_validator(mode="after")
    def _check_bounds(self) -> NumericConstraint:
        if self.operator is Comparator.BETWEEN:
            if self.upper is None:
                raise ValueError("BETWEEN requires `upper`.")
            if self.upper <= self.value:
                raise ValueError("BETWEEN requires upper > value (the lower bound).")
        elif self.upper is not None:
            raise ValueError("`upper` is only valid with operator == BETWEEN.")
        return self
# --------------------------------------------------------------------------- #
# Expression tree — a discriminated union on `node_type`
# --------------------------------------------------------------------------- #
class Atom(BaseModel):
    """A single, optionally time- and value-qualified predicate about one entity."""
    model_config = ConfigDict(extra="forbid")
    node_type: Literal["atom"] = "atom"
    entity: Entity
    temporal: TemporalConstraint | None = None
    numeric: NumericConstraint | None = None
    @model_validator(mode="after")
    def _numeric_target(self) -> Atom:
        if self.numeric is not None and self.entity.type not in _NUMERIC_ENTITY_TYPES:
            raise ValueError(
                f"Numeric constraint attached to non-measurable entity type "
                f"'{self.entity.type.value}'; expected measurement/observation/person."
            )
        return self
class Not(BaseModel):
    """Logical negation of a sub-expression. Scopes over an atom OR a group."""
    model_config = ConfigDict(extra="forbid")
    node_type: Literal["not"] = "not"
    operand: Expression
class BooleanGroup(BaseModel):
    """N-ary AND / OR over >= 2 sub-expressions."""
    model_config = ConfigDict(extra="forbid")
    node_type: Literal["group"] = "group"
    operator: BoolOp
    operands: list[Expression]
    @field_validator("operands")
    @classmethod
    def _min_two(cls, v: list) -> list:
        if len(v) < 2:
            raise ValueError("BooleanGroup requires >= 2 operands; unwrap singletons into the parent.")
        return v
# The recursive node type. Pydantic resolves the forward refs via model_rebuild() below.
Expression = Annotated[
    Atom | BooleanGroup | Not,
    Field(discriminator="node_type"),
]
# --------------------------------------------------------------------------- #
# Top-level criterion
# --------------------------------------------------------------------------- #
class LogicalForm(BaseModel):
    """Harmonized representation of one eligibility criterion (the unit of the benchmark)."""
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION
    criterion_id: str = Field(..., description="Stable id, e.g. 'ctgov:NCT07675850:inc:00'.")
    source: Source
    polarity: Polarity
    text: str = Field(..., description="Verbatim criterion text from the source.")
    expression: Expression
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form provenance (trial id, span offsets, ...)."
    )
    @field_validator("criterion_id", "text")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must be non-empty.")
        return v
    def canonical(self) -> LogicalForm:
        """Return a copy with the expression in canonical normal form (see `canonicalize`)."""
        return self.model_copy(update={"expression": canonicalize(self.expression)})
# Resolve forward references for the recursive discriminated union.
Not.model_rebuild()
BooleanGroup.model_rebuild()
LogicalForm.model_rebuild()
# --------------------------------------------------------------------------- #
# Canonicalization — the normal form Task A scores exact-match against
# --------------------------------------------------------------------------- #
def _key(expr: Expression) -> str:
    """Deterministic sort/dedupe key for a node (AND/OR are commutative)."""
    return expr.model_dump_json()
def canonicalize(expr: Expression) -> Expression:
    """Reduce an expression to a single normal form for exact-match comparison.
    Idempotent. Applies, recursively:
      * flatten nested same-operator groups   (A AND (B AND C)) -> AND(A, B, C)
      * drop structurally duplicate operands
      * sort operands by serialized form
      * collapse double negation              NOT(NOT x) -> x
      * unwrap a group left with one operand   AND(A) -> A
    """
    if isinstance(expr, Atom):
        return expr.model_copy(deep=True)
    if isinstance(expr, Not):
        inner = canonicalize(expr.operand)
        if isinstance(inner, Not):  # NOT(NOT x) -> x
            return inner.operand
        return Not(operand=inner)
    if isinstance(expr, BooleanGroup):
        flattened: list[Expression] = []
        for op in expr.operands:
            c = canonicalize(op)
            if isinstance(c, BooleanGroup) and c.operator == expr.operator:
                flattened.extend(c.operands)  # absorb same-operator child
            else:
                flattened.append(c)
        seen: set[str] = set()
        unique: list[Expression] = []
        for c in flattened:
            k = _key(c)
            if k not in seen:
                seen.add(k)
                unique.append(c)
        unique.sort(key=_key)
        if len(unique) == 1:  # everything collapsed/deduped to one child
            return unique[0]
        return BooleanGroup(operator=expr.operator, operands=unique)
    raise TypeError(f"Unknown expression node: {type(expr)!r}")
# --------------------------------------------------------------------------- #
# Worked examples (also serve as smoke tests under __main__)
# --------------------------------------------------------------------------- #
def example_simple_inclusion() -> LogicalForm:
    """Simple inclusion: a single entity + one numeric constraint.
    'Age 18 years or older.' — a single-atom demographic criterion.
    """
    return LogicalForm(
        criterion_id="example:age-18",
        source=Source.SYNTHETIC_EXAMPLE,
        polarity=Polarity.INCLUSION,
        text="Age 18 years or older.",
        expression=Atom(
            entity=Entity(text="age", type=EntityType.PERSON),
            numeric=NumericConstraint(operator=Comparator.GE, value=18, unit="years"),
        ),
    )
def example_nested_compound() -> LogicalForm:
    """Nested AND/OR/NOT exercising temporal + numeric constraints together.
    'Type 2 diabetes with HbA1c between 6.5% and 9.5%, AND either myocardial
     infarction within the past 6 months OR current aspirin therapy, AND no
     diabetic ketoacidosis within the past year.'
    """
    return LogicalForm(
        criterion_id="example:t2dm-composite",
        source=Source.SYNTHETIC_EXAMPLE,
        polarity=Polarity.INCLUSION,
        text=(
            "Type 2 diabetes mellitus with HbA1c between 6.5% and 9.5%, and either "
            "myocardial infarction within the past 6 months or current aspirin therapy, "
            "and no diabetic ketoacidosis within the past year."
        ),
        expression=BooleanGroup(
            operator=BoolOp.AND,
            operands=[
                Atom(entity=Entity(text="type 2 diabetes mellitus", type=EntityType.CONDITION)),
                Atom(
                    entity=Entity(text="HbA1c", type=EntityType.MEASUREMENT),
                    numeric=NumericConstraint(operator=Comparator.BETWEEN, value=6.5, upper=9.5, unit="%"),
                ),
                BooleanGroup(
                    operator=BoolOp.OR,
                    operands=[
                        Atom(
                            entity=Entity(text="myocardial infarction", type=EntityType.CONDITION),
                            temporal=TemporalConstraint(
                                operator=TemporalOp.WITHIN, value=6, unit=TimeUnit.MONTHS, anchor="enrollment"
                            ),
                        ),
                        Atom(
                            entity=Entity(text="aspirin", type=EntityType.DRUG),
                            temporal=TemporalConstraint(operator=TemporalOp.CURRENT),
                        ),
                    ],
                ),
                Not(
                    operand=Atom(
                        entity=Entity(text="diabetic ketoacidosis", type=EntityType.CONDITION),
                        temporal=TemporalConstraint(
                            operator=TemporalOp.WITHIN, value=1, unit=TimeUnit.YEARS, anchor="enrollment"
                        ),
                    )
                ),
            ],
        ),
    )
if __name__ == "__main__":
    for lf in (example_simple_inclusion(), example_nested_compound()):
        blob = lf.model_dump_json(indent=2)
        # Round-trip invariant: JSON -> object -> JSON is identical.
        assert LogicalForm.model_validate_json(blob).model_dump_json(indent=2) == blob
        print(blob)
        print("-" * 70)
    # Canonicalization is idempotent and order/duplication invariant.
    c = example_nested_compound().canonical()
    assert c.canonical().model_dump_json() == c.model_dump_json()
    print("OK: round-trip + idempotent canonicalization")
