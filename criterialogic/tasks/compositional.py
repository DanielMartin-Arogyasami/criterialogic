"""Arm 2 — the compositional-logic stress test, and its deterministic generator.

Atoms drawn from the ClinicalTrials.gov pool are composed into nested AND/OR/NOT
structures of controlled depth, with a ground-truth label computed by the three-valued
oracle under a sampled patient. Because generation is seeded, the set is regenerable
rather than a black box.

Depth is the independent variable, and that is the point of the arm. A model can be
measured at depth 1 and again at depth 6 over atoms from the same pool with the same
prompt, so a difference in accuracy is attributable to logical structure rather than to
vocabulary, topic, or prompt design. Real criteria do not reach depth 6; the arm is a
stress test, and :mod:`criterialogic.data.real_criteria` is the realism check beside it.

What is real and what is not: the atoms are real trial predicates carrying their source
NCT IDs. The nesting that combines them, and the patients evaluated against them, are
synthetic by construction. Every generated item records
``metadata["composition"] = "synthetic"`` and the pool digest for exactly this reason.
"""
from __future__ import annotations

import random
from collections.abc import Sequence
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

TASK_NAME = "compositional"


def _atom_pool(atom_source: str = CTGOV, path: Path | str = DEFAULT_POOL_PATH) -> list[Atom]:
    """The atoms this arm composes over. Raises if the pool has not been built."""
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


def regenerate_reported_depth_set(
    depth: int,
    n_per_depth: int = 60,
    seed: int | None = None,
    atom_source: str = CTGOV,
    pool_path: Path | str = DEFAULT_POOL_PATH,
    pool: AtomPool | None = None,
) -> list[Item]:
    """Reproduce, exactly, a single-depth set as it was generated for the v0.2 results.

    The reported depth sweep predates the ``depths=`` argument: each set was built by
    generating depths ``1..depth`` and keeping the depth-``depth`` slice, so its items
    depend on the random draws the shallower depths consumed first. The released numbers
    are therefore not reproducible through the ``depths=[d]`` route, and rather than
    quietly leave them unreproducible from the shipped code, this function preserves the
    original path. ``seed`` defaults to ``101 + depth``, the value used in the results.

    New work should use ``generate_compositional_items(depths=[d], ...)``, which varies
    only depth. See results/paper_data.md.
    """
    seed = 101 + depth if seed is None else seed
    items = generate_compositional_items(
        n_per_depth=n_per_depth, max_depth=depth, seed=seed,
        atom_source=atom_source, pool_path=pool_path, pool=pool,
    )
    return [it for it in items if it.depth == depth]


def generate_compositional_items(
    n_per_depth: int = 12,
    max_depth: int = 3,
    seed: int = 29,
    atom_source: str = CTGOV,
    pool_path: Path | str = DEFAULT_POOL_PATH,
    pool: AtomPool | None = None,
    depths: Sequence[int] | None = None,
) -> list[Item]:
    """Build items across nesting depths.

    By default depths are ``1..max_depth``. Pass ``depths`` to generate a set at
    specific depths — ``depths=[6]`` gives a depth-6-only set. This exists because the
    v0.1 route to a single-depth set was to generate ``1..d`` and filter, which meant
    the depth-6 items depended on how many random draws depths 1-5 had consumed first;
    two sets nominally "at depth 6" were not comparable unless the whole ladder below
    them matched. With an explicit depth list the draw for a given (depth, seed) is
    fixed, so a depth sweep varies one thing.

    Deterministic in (seed, depths, pool contents): the same arguments over the same
    pool file regenerate a byte-identical set. ``pool.sha256`` is recorded on every item
    so a set generated against a different pool is distinguishable rather than silently
    mixed.
    """
    pool = pool if pool is not None else load_pool(atom_source, pool_path)
    atoms = pool.atoms
    ladder = list(depths) if depths is not None else list(range(1, max_depth + 1))
    if not ladder or any(d < 1 for d in ladder):
        raise ValueError(f"depths must be >= 1; got {ladder}")
    rng = random.Random(seed)
    items: list[Item] = []
    for depth in ladder:
        for i in range(n_per_depth):
            expr = _build_expr(depth, atoms, rng)
            used = _collect_atoms(expr)
            nct_ids = pool.nct_ids_for(used)
            metadata = {
                "atom_source": pool.source,
                "atom_pool_sha256": pool.sha256,
                "composition": "synthetic",
                "generator_seed": str(seed),
                "generator_depths": ",".join(str(d) for d in ladder),
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
            facts: dict[str, Fact] = {}
            for atom in used:
                f = _sample_fact_for_atom(atom, rng)
                if f is not None:
                    facts[atom.entity.text] = f
            patient = PatientFacts(record_id=f"synthD-{depth}-{i:03d}", facts=facts)
            items.append(Item(
                item_id=f"comp:d{depth}:{i:03d}",
                task=TASK_NAME,
                criterion=form,
                facts=patient,
                gold=is_met(form, patient),
                depth=expression_depth(expr),
            ))
    return items
