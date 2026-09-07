"""Heuristic error labelling — a triage aid, never the gold taxonomy.

The paper's taxonomy distribution is produced by two human annotators working from
docs/CODEBOOK.md. What this module does is pre-sort the error set so that human pass is
cheaper, and provide an independent, fully reproducible third signal to report agreement
against. Neither annotator sees its output while labelling
(:mod:`criterialogic.taxonomy.reliability` enforces that by writing the annotator files
without the automatic column).

How it decides
--------------
Counterfactual probing on the structured form: rebuild the expression with one feature
removed, re-evaluate against the same patient facts, and ask whether that would have
produced the model's wrong answer. If ignoring negation reproduces the answer, the model
plausibly ignored negation. The probes run in a fixed order:

1. ``unanswerable`` gate (below) — checked first, because an item the prompt cannot
   answer is not evidence about reasoning at all.
2. negation removed             -> NEGATION_POLARITY
3. temporal constraints removed -> TEMPORAL
4. numeric constraints removed  -> NUMERIC_THRESHOLD
5. any nesting present          -> LOGICAL_COMPOSITION
6. otherwise                    -> NONE (unattributed)

Why the order changed in v2
---------------------------
v1 tested "is the expression nested?" *before* the temporal and numeric probes. Since
every item in the compositional arm is nested by construction, that branch caught them
all, and only two of the seven categories were ever reachable — so the v1 distribution
described the labeller rather than the model. Recomputing the v0.2 error set with the
corrected order moves 9 of 87 errors out of ``logical_composition`` into ``temporal``
and ``numeric_threshold``. ``LABELLER_VERSION`` is recorded in every result file so a
distribution can be attributed to the version that produced it.

What it structurally cannot do
------------------------------
ENTITY_CONFLATION, IMPLICIT_KNOWLEDGE and FABRICATION are not reachable by any
counterfactual over the structured form: they concern the relationship between the
criterion text and the world, not between the expression and the facts. Those three are
human-only, and :func:`reachable_categories` states that in code so a report can say it
rather than leave a reader to infer it from three empty rows.
"""
from __future__ import annotations

from collections import Counter

from criterialogic.oracle import evaluate
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    Expression,
    Not,
    TemporalOp,
)
from criterialogic.tasks.base import expression_depth
from criterialogic.taxonomy.categories import FailureCategory

#: Bumped whenever a probe or the decision order changes, so a reported distribution is
#: attributable to the code that produced it.
LABELLER_VERSION = "2"

HUMAN_ONLY_CATEGORIES = {
    FailureCategory.ENTITY_CONFLATION,
    FailureCategory.IMPLICIT_KNOWLEDGE,
    FailureCategory.FABRICATION,
}


def reachable_categories() -> set[FailureCategory]:
    """Categories this labeller can assign. The rest are human-only by construction."""
    return {
        FailureCategory.NEGATION_POLARITY,
        FailureCategory.TEMPORAL,
        FailureCategory.NUMERIC_THRESHOLD,
        FailureCategory.LOGICAL_COMPOSITION,
        FailureCategory.NONE,
    }


# --------------------------------------------------------------------------- #
# Structural probes
# --------------------------------------------------------------------------- #
def _has(expr: Expression, attr: str) -> bool:
    if isinstance(expr, Atom):
        return getattr(expr, attr) is not None
    if isinstance(expr, Not):
        return _has(expr.operand, attr)
    if isinstance(expr, BooleanGroup):
        return any(_has(op, attr) for op in expr.operands)
    return False


def _contains_not(expr: Expression) -> bool:
    if isinstance(expr, Not):
        return True
    if isinstance(expr, BooleanGroup):
        return any(_contains_not(op) for op in expr.operands)
    return False


def _strip_negation(expr: Expression) -> Expression:
    if isinstance(expr, Atom):
        return expr
    if isinstance(expr, Not):
        return _strip_negation(expr.operand)
    if isinstance(expr, BooleanGroup):
        return BooleanGroup(operator=expr.operator,
                            operands=[_strip_negation(o) for o in expr.operands])
    raise TypeError(type(expr))


def _drop_constraint(expr: Expression, attr: str) -> Expression:
    """Return the expression with every ``attr`` constraint removed from its atoms."""
    if isinstance(expr, Atom):
        return expr.model_copy(update={attr: None})
    if isinstance(expr, Not):
        return Not(operand=_drop_constraint(expr.operand, attr))
    if isinstance(expr, BooleanGroup):
        return BooleanGroup(operator=expr.operator,
                            operands=[_drop_constraint(o, attr) for o in expr.operands])
    raise TypeError(type(expr))


def _atoms(expr: Expression) -> list[Atom]:
    if isinstance(expr, Atom):
        return [expr]
    if isinstance(expr, Not):
        return _atoms(expr.operand)
    if isinstance(expr, BooleanGroup):
        out: list[Atom] = []
        for op in expr.operands:
            out.extend(_atoms(op))
        return out
    raise TypeError(type(expr))


# --------------------------------------------------------------------------- #
# Answerability
# --------------------------------------------------------------------------- #
def unanswerable_reasons(item, prompt_version: str | None = "1") -> list[str]:
    """Ways this item's gold label rests on something the prompt does not state.

    **Answerability is a property of the item *and* the renderer**, which is why the
    version is a parameter. Renderer v2 states the currency of every present finding, so
    nothing is unanswerable under it and this returns empty. Under v1 the check below
    applies. ``prompt_version=None`` means no prompt was involved at all — the offline
    diagnostics evaluate the structured form directly — so nothing is unanswerable there
    either.

    Getting this wrong in the other direction is the trap: leaving the flag renderer-blind
    would keep firing after the v2 re-run, and ``failure_breakdown`` would go on withholding
    those errors from the taxonomy, understating error attribution in exactly the run that
    was supposed to fix the problem.

    Currently one, and it is the reason this function exists. ``Fact.current`` is a
    plain ``bool`` defaulting to ``False``, and the oracle reads ``current=False`` as a
    definite *false* for a ``CURRENT``-scoped atom. Prompt renderer v1 emits
    "currently active" only when the flag is true and emits nothing when it is false, so
    a present-but-not-current fact renders as ``- x: present`` — textually identical to a
    fact whose currency was never recorded. A model that answers "satisfied" there has
    read the prompt correctly; the gold label disagrees on the strength of a field the
    prompt does not contain.

    Errors on these items are excluded from the taxonomy distribution and counted
    separately. They are renderer defects being scored as reasoning failures, and in the
    v0.2 depth sweep they are the majority of the deep-item errors — see
    results/SECTION7.md. Renderer v2 makes the rendering total and removes the defect at
    the cost of invalidating the cached v0.2 responses.
    """
    if prompt_version != "1":
        return []
    reasons: list[str] = []
    for atom in _atoms(item.criterion.expression):
        if atom.temporal is None or atom.temporal.operator is not TemporalOp.CURRENT:
            continue
        fact = item.facts.get(atom.entity.text)
        if fact is not None and fact.present and not fact.current:
            reasons.append(f"current_unstated:{atom.entity.text}")
    return reasons


def is_unanswerable(item, prompt_version: str | None = "1") -> bool:
    return bool(unanswerable_reasons(item, prompt_version))


# --------------------------------------------------------------------------- #
# Categorisation
# --------------------------------------------------------------------------- #
def categorize_error(item, prediction) -> FailureCategory:
    """Heuristic failure category for one (item, prediction). See the module docstring."""
    if prediction.label == item.gold:
        return FailureCategory.NONE
    expr = item.criterion.expression

    def reproduces(alt: Expression) -> bool:
        value = evaluate(alt, item.facts)
        return value is not None and bool(value) == prediction.label

    if _contains_not(expr) and reproduces(_strip_negation(expr)):
        return FailureCategory.NEGATION_POLARITY
    if _has(expr, "temporal") and reproduces(_drop_constraint(expr, "temporal")):
        return FailureCategory.TEMPORAL
    if _has(expr, "numeric") and reproduces(_drop_constraint(expr, "numeric")):
        return FailureCategory.NUMERIC_THRESHOLD
    if expression_depth(expr) >= 1:
        return FailureCategory.LOGICAL_COMPOSITION
    # A single flat atom, wrong, and no probe explains it. v1 guessed
    # IMPLICIT_KNOWLEDGE here; that category requires knowing what the model needed to
    # infer, which no counterfactual over the form can establish. Leave it to the human.
    return FailureCategory.NONE


def failure_breakdown(items, predictions, exclude_unanswerable: bool = True,
                      prompt_version: str | None = "1") -> dict:
    """Per-category error counts, plus the counts a reader needs to size the evidence.

    ``distinct_rationales`` is reported beside the raw error count because five items
    that share one verbatim rationale are one systematic misreading replicated five
    times, not five independent observations. Computing a taxonomy percentage over raw
    errors in that situation overstates the evidence, which the v0.1 audit flagged.
    """
    pred_by_id = {p.item_id: p for p in predictions}
    counts: Counter = Counter()
    rationales: list[str] = []
    n_errors = 0
    n_unanswerable = 0
    withheld: Counter = Counter()

    for item in items:
        pred = pred_by_id[item.item_id]
        if pred.label == item.gold:
            continue
        n_errors += 1
        if pred.rationale:
            rationales.append(pred.rationale.strip())
        if is_unanswerable(item, prompt_version):
            n_unanswerable += 1
            withheld[categorize_error(item, pred).value] += 1
            if exclude_unanswerable:
                continue
        counts[categorize_error(item, pred).value] += 1

    return {
        "labeller_version": LABELLER_VERSION,
        "categories": dict(sorted(counts.items())),
        "n_errors": n_errors,
        "n_errors_scored": sum(counts.values()),
        "n_errors_unanswerable": n_unanswerable,
        "unanswerable_categories_withheld": dict(sorted(withheld.items())),
        "distinct_rationales": len(set(rationales)),
        "largest_rationale_cluster": max(Counter(rationales).values()) if rationales else 0,
        "unanswerable_excluded": exclude_unanswerable,
        "prompt_version_assessed": prompt_version,
        "human_only_categories": sorted(c.value for c in HUMAN_ONLY_CATEGORIES),
    }
