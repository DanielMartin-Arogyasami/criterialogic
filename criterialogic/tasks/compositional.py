"""Task D — compositional-logic stress test + its deterministic generator.
Atoms drawn from a pool (here, the leaf predicates of the n2c2 criteria) are
composed into nested AND/OR/NOT structures of controlled depth, with a known
ground-truth label (the oracle) under a sampled patient. Because generation is
seeded, the synthetic set is regenerable rather than a black box (spec §11).
"""
from __future__ import annotations

import random

from criterialogic.data.n2c2_criteria import n2c2_criteria_as_logical_forms
from criterialogic.data.synthetic import _collect_atoms, _sample_fact_for_atom
from criterialogic.oracle import Fact, PatientFacts, is_met
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Expression,
    LogicalForm,
    Not,
    Polarity,
    Source,
)
from criterialogic.tasks.base import Item, expression_depth


def _atom_pool() -> list[Atom]:
    pool: list[Atom] = []
    seen: set[str] = set()
    for form in n2c2_criteria_as_logical_forms():
        for atom in _collect_atoms(form.expression):
            key = atom.model_dump_json()
            if key not in seen:
                seen.add(key)
                pool.append(atom)
    return pool
def _build_expr(depth: int, pool: list[Atom], rng: random.Random) -> Expression:
    """Recursively build an expression of (at most) the requested nesting depth."""
    if depth <= 0:
        atom = rng.choice(pool)
        return Not(operand=atom) if rng.random() < 0.25 else atom
    op = rng.choice([BoolOp.AND, BoolOp.OR])
    k = rng.choice([2, 2, 3])
    operands = [_build_expr(depth - 1, pool, rng) for _ in range(k)]
    group: Expression = BooleanGroup(operator=op, operands=operands)
    return Not(operand=group) if rng.random() < 0.15 else group
def generate_compositional_items(
    n_per_depth: int = 12, max_depth: int = 3, seed: int = 29
) -> list[Item]:
    """Build Task-D items across nesting depths 1..max_depth."""
    rng = random.Random(seed)
    pool = _atom_pool()
    items: list[Item] = []
    for depth in range(1, max_depth + 1):
        for i in range(n_per_depth):
            expr = _build_expr(depth, pool, rng)
            form = LogicalForm(
                criterion_id=f"ctgov:synth:d{depth}:{i:03d}",
                source=Source.CTGOV_SYNTHETIC,
                polarity=Polarity.INCLUSION,
                text="(synthetic compositional criterion)",
                expression=expr,
                metadata={"synthetic": "true"},
            )
            # sample a patient over this expression's atoms
            facts: dict[str, Fact] = {}
            for atom in _collect_atoms(expr):
                f = _sample_fact_for_atom(atom, rng)
                if f is not None:
                    facts[atom.entity.text] = f
            patient = PatientFacts(record_id=f"synthD-{depth}-{i:03d}", facts=facts)
            items.append(Item(
                item_id=f"comp:d{depth}:{i:03d}",
                task="compositional",
                criterion=form,
                facts=patient,
                gold=is_met(form, patient),
                depth=expression_depth(expr),
            ))
    return items
