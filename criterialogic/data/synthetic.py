"""Deterministic synthetic patient-fact generation for the runnable demo.
Real criteria (n2c2) + synthetic patients let the full pipeline run with **no
external data**. Generation is seeded and regenerable — never a black box.
Facts are sampled so that each criterion gets a mix of met / not-met / unknown
cases, and the gold label is computed by the oracle (`criterialogic.oracle`).
"""
from __future__ import annotations

import random

from criterialogic.oracle import Fact, PatientFacts, is_met
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    Comparator,
    Expression,
    LogicalForm,
    Not,
)


def _collect_atoms(expr: Expression) -> list[Atom]:
    if isinstance(expr, Atom):
        return [expr]
    if isinstance(expr, Not):
        return _collect_atoms(expr.operand)
    if isinstance(expr, BooleanGroup):
        out: list[Atom] = []
        for op in expr.operands:
            out.extend(_collect_atoms(op))
        return out
    raise TypeError(type(expr))
def _sample_fact_for_atom(atom: Atom, rng: random.Random) -> Fact | None:
    """Produce a plausible fact (or None = absent) that sometimes satisfies the atom."""
    if rng.random() < 0.2:
        return None  # entity simply absent from the record
    present = rng.random() < 0.8
    fact = Fact(present=present)
    if atom.numeric is not None:
        c = atom.numeric
        # center the sample near the threshold so both sides occur
        if c.operator is Comparator.BETWEEN:
            center = (c.value + (c.upper or c.value)) / 2.0
            fact.value = round(rng.uniform(center - 3, center + 3), 2)
        else:
            fact.value = round(c.value + rng.uniform(-2.5, 2.5), 2)
    if atom.temporal is not None:
        op = atom.temporal.operator.value
        if op == "current":
            fact.current = rng.random() < 0.5
            fact.present = fact.present or fact.current
        elif op == "any_history":
            pass
        else:  # windowed: sample a recency on both sides of the window
            base_days = (atom.temporal.value or 1) * 30.4375
            fact.days_ago = round(rng.uniform(0.2 * base_days, 2.2 * base_days), 1)
    return fact
def make_patient_for_criterion(form: LogicalForm, record_id: str, rng: random.Random) -> PatientFacts:
    facts: dict[str, Fact] = {}
    for atom in _collect_atoms(form.expression):
        f = _sample_fact_for_atom(atom, rng)
        if f is not None:
            facts[atom.entity.text] = f
    return PatientFacts(record_id=record_id, facts=facts)
def generate_matching_items(
    forms: list[LogicalForm], n_per_criterion: int = 8, seed: int = 13
):
    """Build Task-C items: each criterion paired with `n_per_criterion` synthetic patients."""
    from criterialogic.tasks.base import Item  # local import to avoid a cycle
    rng = random.Random(seed)
    items: list[Item] = []
    for form in forms:
        tag = form.metadata.get("tag", form.criterion_id)
        for i in range(n_per_criterion):
            rid = f"{tag}-P{i:03d}"
            facts = make_patient_for_criterion(form, rid, rng)
            items.append(Item(
                item_id=f"match:{tag}:{i:03d}",
                task="matching",
                criterion=form,
                facts=facts,
                gold=is_met(form, facts),
                group=tag,
            ))
    return items
