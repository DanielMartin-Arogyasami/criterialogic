"""Task D — compositional-logic stress test + its deterministic generator.

Atoms drawn from a pool are composed into nested AND/OR/NOT structures of controlled
depth, with a known ground-truth label (the oracle) under a sampled patient. Because
generation is seeded, the synthetic set is regenerable rather than a black box (spec §11).

The default pool is `ctgov`: predicates extracted from verbatim ClinicalTrials.gov
eligibility text, each traceable to its source trial (see
:mod:`criterialogic.data.atom_pool`). Every generated item records which pool it used
and the NCT IDs behind its atoms. The `n2c2_derived` pool remains available but must be
requested explicitly.

What is real and what is not: the atoms are real trial predicates; the nesting that
combines them, and the patients evaluated against them, are synthetic by construction.
"""
from __future__ import annotations

import random
from pathlib import Path

from criterialogic.data.atom_pool import CTGOV, DEFAULT_POOL_PATH, AtomPool, load_pool
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
)
from criterialogic.tasks.base import Item, expression_depth


def _atom_pool(atom_source: str = CTGOV, path: Path | str = DEFAULT_POOL_PATH) -> list[Atom]:
    """The atoms Task D composes over. Raises if the requested pool has not been built."""
    return load_pool(atom_source, path).atoms


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
    n_per_depth: int = 12,
    max_depth: int = 3,
    seed: int = 29,
    atom_source: str = CTGOV,
    pool_path: Path | str = DEFAULT_POOL_PATH,
    pool: AtomPool | None = None,
) -> list[Item]:
    """Build Task-D items across nesting depths 1..max_depth.

    Deterministic in (seed, pool contents): the same seed over the same pool file
    regenerates a byte-identical set. `pool.sha256` is recorded on every item so a set
    generated against a different pool is distinguishable rather than silently mixed.
    """
    pool = pool if pool is not None else load_pool(atom_source, pool_path)
    atoms = pool.atoms
    rng = random.Random(seed)
    items: list[Item] = []
    for depth in range(1, max_depth + 1):
        for i in range(n_per_depth):
            expr = _build_expr(depth, atoms, rng)
            used = _collect_atoms(expr)
            nct_ids = pool.nct_ids_for(used)
            metadata = {
                "atom_source": pool.source,
                "atom_pool_sha256": pool.sha256,
                "composition": "synthetic",
                "generator_seed": str(seed),
            }
            if nct_ids:
                metadata["source_nct_ids"] = ",".join(nct_ids)
            form = LogicalForm(
                criterion_id=f"{pool.source}:comp:d{depth}:{i:03d}",
                source=pool.logical_form_source,
                polarity=Polarity.INCLUSION,
                text="(synthetic composition over real extracted atoms)",
                expression=expr,
                metadata=metadata,
            )
            # sample a patient over this expression's atoms
            facts: dict[str, Fact] = {}
            for atom in used:
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
