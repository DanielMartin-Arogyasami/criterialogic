"""The 13 n2c2 2018 Track-1 selection criteria, encoded as harmonized LogicalForms.
The criterion *definitions* are public (from the shared-task description, Stubbs
et al., JAMIA 2019); only the patient records are DUA-gated. Encoding them here
(a) demonstrates the n2c2 -> schema mapping concretely and (b) provides real
criteria for the runnable demo, paired with synthetic patient facts.
KNOWN MODELING NOTE — cardinality:
  ADVANCED-CAD is "two or more of {N indicators}". The schema's connectives are
  AND/OR/NOT only (no native k-of-n), so it is expanded to disjunctive normal
  form (an OR over all 2-subsets). This is exact but verbose; a `Cardinality`
  node is a candidate v2 extension. See TRADEOFFS in the paper.
"""
from __future__ import annotations

from itertools import combinations

from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Entity,
    EntityType,
    Expression,
    LogicalForm,
    NumericConstraint,
    Polarity,
    Source,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
)


def _cond(text: str) -> Atom:
    return Atom(entity=Entity(text=text, type=EntityType.CONDITION))
def _at_least_k_of(atoms: list[Expression], k: int) -> Expression:
    """Express 'at least k of these' as DNF: OR over all k-subset ANDs."""
    clauses = [BooleanGroup(operator=BoolOp.AND, operands=list(c)) for c in combinations(atoms, k)]
    return BooleanGroup(operator=BoolOp.OR, operands=clauses)
def n2c2_criteria_as_logical_forms() -> list[LogicalForm]:
    """Return all 13 criteria as LogicalForm records (source = n2c2_2018)."""
    def lf(tag: str, text: str, polarity: Polarity, expr: Expression) -> LogicalForm:
        return LogicalForm(
            criterion_id=f"n2c2:{tag}",
            source=Source.N2C2_2018,
            polarity=polarity,
            text=text,
            expression=expr,
            metadata={"tag": tag},
        )
    forms: list[LogicalForm] = []
    forms.append(lf(
        "ABDOMINAL",
        "History of intra-abdominal surgery, small or large intestine resection, or small bowel obstruction.",
        Polarity.INCLUSION,
        BooleanGroup(operator=BoolOp.OR, operands=[
            _cond("intra-abdominal surgery"),
            _cond("intestine resection"),
            _cond("small bowel obstruction"),
        ]),
    ))
    # ADVANCED-CAD: >= 2 of {>=2 CAD meds, history of MI, current angina, ischemia}
    cad_indicators: list[Expression] = [
        Atom(entity=Entity(text="cad medication count", type=EntityType.MEASUREMENT),
             numeric=NumericConstraint(operator=Comparator.GE, value=2, unit="count")),
        Atom(entity=Entity(text="myocardial infarction", type=EntityType.CONDITION),
             temporal=TemporalConstraint(operator=TemporalOp.ANY_HISTORY)),
        Atom(entity=Entity(text="angina", type=EntityType.CONDITION),
             temporal=TemporalConstraint(operator=TemporalOp.CURRENT)),
        _cond("ischemia"),
    ]
    forms.append(lf(
        "ADVANCED-CAD",
        "Advanced cardiovascular disease: two or more of (>=2 CAD medications; history of MI; "
        "current angina; ischemia).",
        Polarity.INCLUSION,
        _at_least_k_of(cad_indicators, 2),
    ))
    forms.append(lf(
        "ALCOHOL-ABUSE",
        "Current alcohol use over the weekly recommended limit.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="alcohol abuse", type=EntityType.LIFESTYLE),
             temporal=TemporalConstraint(operator=TemporalOp.CURRENT)),
    ))
    forms.append(lf(
        "ASP-FOR-MI",
        "Use of aspirin to prevent myocardial infarction.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="aspirin for mi prophylaxis", type=EntityType.DRUG),
             temporal=TemporalConstraint(operator=TemporalOp.CURRENT)),
    ))
    forms.append(lf(
        "CREATININE",
        "Serum creatinine above the upper limit of normal.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="serum creatinine", type=EntityType.MEASUREMENT,
                           codes={"note": "ULN is lab-specific; 1.3 mg/dL used for synthetic eval"}),
             numeric=NumericConstraint(operator=Comparator.GT, value=1.3, unit="mg/dL")),
    ))
    forms.append(lf(
        "DIETSUPP-2MOS",
        "Taken a dietary supplement (excluding vitamin D) in the past 2 months.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="dietary supplement excluding vitamin d", type=EntityType.DRUG),
             temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=2, unit=TimeUnit.MONTHS)),
    ))
    forms.append(lf(
        "DRUG-ABUSE",
        "Drug abuse, current or past.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="drug abuse", type=EntityType.LIFESTYLE),
             temporal=TemporalConstraint(operator=TemporalOp.ANY_HISTORY)),
    ))
    forms.append(lf(
        "ENGLISH",
        "Patient must speak English.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="speaks english", type=EntityType.OBSERVATION)),
    ))
    forms.append(lf(
        "HBA1C",
        "Any HbA1c value between 6.5% and 9.5%.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="HbA1c", type=EntityType.MEASUREMENT),
             numeric=NumericConstraint(operator=Comparator.BETWEEN, value=6.5, upper=9.5, unit="%")),
    ))
    forms.append(lf(
        "KETO-1YR",
        "Diagnosis of ketoacidosis within the past year.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="ketoacidosis", type=EntityType.CONDITION),
             temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=1, unit=TimeUnit.YEARS)),
    ))
    forms.append(lf(
        "MAJOR-DIABETES",
        "Major diabetes-related complication (amputation, nephropathy, retinopathy, or neuropathy).",
        Polarity.INCLUSION,
        BooleanGroup(operator=BoolOp.OR, operands=[
            _cond("amputation"),
            _cond("diabetic nephropathy"),
            _cond("diabetic retinopathy"),
            _cond("diabetic neuropathy"),
        ]),
    ))
    forms.append(lf(
        "MAKES-DECISIONS",
        "Patient must make their own medical decisions.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="makes own medical decisions", type=EntityType.OBSERVATION)),
    ))
    forms.append(lf(
        "MI-6MOS",
        "Myocardial infarction in the past 6 months.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="myocardial infarction", type=EntityType.CONDITION),
             temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=6, unit=TimeUnit.MONTHS)),
    ))
    return forms
# Convenience: the canonical tag list, in the official order.
N2C2_TAGS = [
    "ABDOMINAL", "ADVANCED-CAD", "ALCOHOL-ABUSE", "ASP-FOR-MI", "CREATININE",
    "DIETSUPP-2MOS", "DRUG-ABUSE", "ENGLISH", "HBA1C", "KETO-1YR",
    "MAJOR-DIABETES", "MAKES-DECISIONS", "MI-6MOS",
]
