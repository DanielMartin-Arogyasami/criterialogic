"""Arm 2, size-matched — depth varies, size and operator count do not.

In the released depth sweep every branch of a generated tree runs to the full depth,
with two or three operands per group, so the number of predicates grows about 2.3x per
level: about 5 leaves at depth 2 and about 150 at depth 6. Depth and size are then
almost perfectly correlated (r = 0.98 between depth and log2(leaves)), and no analysis
of those sets can say which of the two the model is responding to.

This generator holds fixed, at every depth:

* the number of leaves (atoms),
* the number of Boolean groups (so the number of AND/OR operators),
* the number of NOT nodes,
* the gold base rate: each depth is filled to exactly half met, half not met.

Depth is set by the shape of the tree alone. A chain of ``depth`` groups fixes the
height; the remaining groups attach under groups above the bottom level; atoms are
distributed so that every group has at least two operands. AND and OR alternate along
every path, so no group sits directly inside a group with the same operator and
canonicalisation cannot flatten any level away: nominal depth equals canonical depth.
Because the root operator is drawn 50/50, AND and OR are balanced in expectation at
every depth.

Atoms come from the same pool and patients from the same fact sampler as the released
sets, so the only systematic difference between depth levels is the shape of the tree.
Deterministic in (seed, depths, leaves, groups, nots, n_per_depth, pool contents).

The companion design, :func:`generate_size_sweep_items`, does the converse: depth is
held at 3 while the number of leaves doubles from 7 to 112, with groups and NOT nodes
scaled in the same ratio as the size-matched set (6 groups and 4 NOTs per 14 leaves), so
the 14-leaf level reproduces the size-matched set's depth-3 configuration. Together the
two sets vary depth at fixed size and size at fixed depth.
"""
from __future__ import annotations

import random
from collections.abc import Sequence
from pathlib import Path

from criterialogic.data.atom_pool import CTGOV, DEFAULT_POOL_PATH, AtomPool, load_pool
from criterialogic.data.synthetic import _sample_fact_for_atom
from criterialogic.oracle import Fact, PatientFacts, is_met
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Expression,
    LogicalForm,
    Not,
    Polarity,
    canonicalize,
)
from criterialogic.tasks.base import Item, expression_depth

TASK_NAME = "compositional"  # scored and reported exactly like the released sets
DEFAULT_LEAVES = 14
DEFAULT_GROUPS = 6
DEFAULT_NOTS = 4
DEFAULT_DEPTHS = (2, 3, 4, 5, 6)


def _check_params(n_leaves: int, n_groups: int, n_nots: int, depths: Sequence[int]) -> None:
    if not depths:
        raise ValueError("depths must not be empty")
    if any(d < 1 or d > n_groups for d in depths):
        raise ValueError(f"every depth must lie in 1..n_groups ({n_groups}); got {list(depths)}")
    if n_groups > 1 and min(depths) == 1:
        raise ValueError("depth 1 is a single group, so it needs n_groups == 1")
    # The worst case is a star: n_groups - 1 bottom-level groups, each needing two atoms.
    if n_leaves < max(2, 2 * (n_groups - 1)):
        raise ValueError(f"n_leaves must be at least {max(2, 2 * (n_groups - 1))} for {n_groups} groups")
    if not 0 <= n_nots <= n_leaves + n_groups:
        raise ValueError("n_nots must lie between 0 and the number of nodes")


def _skeleton(n_groups: int, depth: int, rng: random.Random) -> tuple[list[int | None], list[int]]:
    """Parent index and level for each group; group 0 is the root at level 1."""
    parent: list[int | None] = [None]
    level = [1]
    for i in range(1, depth):  # the chain that fixes the height
        parent.append(i - 1)
        level.append(i + 1)
    for _ in range(n_groups - depth):
        eligible = [g for g, lv in enumerate(level) if lv < depth]
        p = rng.choice(eligible)
        parent.append(p)
        level.append(level[p] + 1)
    return parent, level


def build_matched_expression(
    depth: int,
    pool: list[Atom],
    rng: random.Random,
    n_leaves: int = DEFAULT_LEAVES,
    n_groups: int = DEFAULT_GROUPS,
    n_nots: int = DEFAULT_NOTS,
) -> Expression:
    """One expression with exactly the given depth, leaves, groups and NOT nodes."""
    _check_params(n_leaves, n_groups, n_nots, [depth])
    parent, _ = _skeleton(n_groups, depth, rng)
    children: list[list[int]] = [[] for _ in range(n_groups)]
    for g, p in enumerate(parent):
        if p is not None:
            children[p].append(g)
    n_atoms = [max(0, 2 - len(children[g])) for g in range(n_groups)]
    for _ in range(n_leaves - sum(n_atoms)):
        n_atoms[rng.randrange(n_groups)] += 1

    ops: list[BoolOp] = [rng.choice([BoolOp.AND, BoolOp.OR])]
    for g in range(1, n_groups):
        ops.append(BoolOp.OR if ops[parent[g]] is BoolOp.AND else BoolOp.AND)

    atoms = iter(rng.sample(pool, n_leaves))  # distinct atoms within an item
    negated = set(rng.sample(range(n_groups + n_leaves), n_nots))  # node ids: groups first
    next_atom_id = [n_groups]

    def wrap(node: Expression, node_id: int) -> Expression:
        return Not(operand=node) if node_id in negated else node

    def build(g: int) -> Expression:
        operands: list[Expression] = [build(c) for c in children[g]]
        for _ in range(n_atoms[g]):
            operands.append(wrap(next(atoms), next_atom_id[0]))
            next_atom_id[0] += 1
        rng.shuffle(operands)
        return wrap(BooleanGroup(operator=ops[g], operands=operands), g)

    return build(0)


def _fill_level(
    *,
    depth: int,
    n_items: int,
    n_leaves: int,
    n_groups: int,
    n_nots: int,
    pool: AtomPool,
    rng: random.Random,
    id_prefix: str,
    record_prefix: str,
    metadata: dict,
    max_attempts_per_item: int,
) -> list[Item]:
    """Draw items with fixed structure until half are met and half are not."""
    quota = {True: n_items // 2, False: n_items - n_items // 2}
    accepted: list[Item] = []
    attempts = 0
    while quota[True] or quota[False]:
        attempts += 1
        if attempts > max_attempts_per_item * n_items:
            raise RuntimeError(f"could not fill {id_prefix}: quota left {quota}")
        expr = build_matched_expression(depth, pool.atoms, rng, n_leaves, n_groups, n_nots)
        if expression_depth(expr) != depth or expression_depth(canonicalize(expr)) != depth:
            continue  # cannot happen by construction; kept as a guard
        facts: dict[str, Fact] = {}
        for atom in _leaves(expr):
            f = _sample_fact_for_atom(atom, rng)
            if f is not None:
                facts[atom.entity.text] = f
        i = len(accepted)
        meta = dict(metadata)
        nct_ids = pool.nct_ids_for(_leaves(expr))
        if nct_ids:
            meta["source_nct_ids"] = ",".join(nct_ids)
        form = LogicalForm(
            criterion_id=f"{pool.source}:{id_prefix}:{i:03d}",
            source=pool.logical_form_source,
            polarity=Polarity.INCLUSION,
            text="(synthetic composition over real extracted atoms)",
            expression=expr,
            metadata=meta,
        )
        patient = PatientFacts(record_id=f"{record_prefix}-{i:03d}", facts=facts)
        gold = is_met(form, patient)
        if not quota[gold]:
            continue
        quota[gold] -= 1
        accepted.append(Item(item_id=f"{id_prefix}:{i:03d}", task=TASK_NAME,
                             criterion=form, facts=patient, gold=gold, depth=depth))
    return accepted


def generate_size_matched_items(
    depths: Sequence[int] = DEFAULT_DEPTHS,
    n_per_depth: int = 100,
    seed: int = 29,
    n_leaves: int = DEFAULT_LEAVES,
    n_groups: int = DEFAULT_GROUPS,
    n_nots: int = DEFAULT_NOTS,
    atom_source: str = CTGOV,
    pool_path: Path | str = DEFAULT_POOL_PATH,
    pool: AtomPool | None = None,
    max_attempts_per_item: int = 200,
) -> list[Item]:
    """Build a set in which only depth varies. Gold is balanced to half met per depth."""
    _check_params(n_leaves, n_groups, n_nots, depths)
    pool = pool if pool is not None else load_pool(atom_source, pool_path)
    rng = random.Random(seed)
    items: list[Item] = []
    for depth in depths:
        metadata = {
            "atom_source": pool.source,
            "atom_pool_sha256": pool.sha256,
            "composition": "synthetic",
            "generator": "size_matched",
            "generator_seed": str(seed),
            "generator_depths": ",".join(str(d) for d in depths),
            "n_leaves": str(n_leaves),
            "n_groups": str(n_groups),
            "n_nots": str(n_nots),
        }
        items.extend(_fill_level(depth=depth, n_items=n_per_depth, n_leaves=n_leaves,
                                 n_groups=n_groups, n_nots=n_nots, pool=pool, rng=rng,
                                 id_prefix=f"match:d{depth}", record_prefix=f"synthM-{depth}",
                                 metadata=metadata, max_attempts_per_item=max_attempts_per_item))
    return items


#: Sizes for the fixed-depth sweep: (leaves, groups, NOT nodes). Leaves double from 7 to
#: 112; groups and NOTs keep the size-matched set's ratio (6 and 4 per 14 leaves), so the
#: second level is exactly the size-matched configuration.
DEFAULT_SWEEP_DEPTH = 3
DEFAULT_SWEEP_SIZES = ((7, 3, 2), (14, 6, 4), (28, 12, 8), (56, 24, 16), (112, 48, 32))


def generate_size_sweep_items(
    sizes: Sequence[tuple[int, int, int]] = DEFAULT_SWEEP_SIZES,
    depth: int = DEFAULT_SWEEP_DEPTH,
    n_per_size: int = 100,
    seed: int = 29,
    atom_source: str = CTGOV,
    pool_path: Path | str = DEFAULT_POOL_PATH,
    pool: AtomPool | None = None,
    max_attempts_per_item: int = 200,
) -> list[Item]:
    """Build a set in which only size varies: depth fixed, gold half met at every size."""
    for n_leaves, n_groups, n_nots in sizes:
        _check_params(n_leaves, n_groups, n_nots, [depth])
    pool = pool if pool is not None else load_pool(atom_source, pool_path)
    rng = random.Random(seed)
    items: list[Item] = []
    for n_leaves, n_groups, n_nots in sizes:
        metadata = {
            "atom_source": pool.source,
            "atom_pool_sha256": pool.sha256,
            "composition": "synthetic",
            "generator": "size_sweep",
            "generator_seed": str(seed),
            "generator_sizes": ";".join(f"{a},{b},{c}" for a, b, c in sizes),
            "n_leaves": str(n_leaves),
            "n_groups": str(n_groups),
            "n_nots": str(n_nots),
        }
        items.extend(_fill_level(depth=depth, n_items=n_per_size, n_leaves=n_leaves,
                                 n_groups=n_groups, n_nots=n_nots, pool=pool, rng=rng,
                                 id_prefix=f"size:L{n_leaves:03d}", record_prefix=f"synthS-{n_leaves}",
                                 metadata=metadata, max_attempts_per_item=max_attempts_per_item))
    return items


def _leaves(expr: Expression) -> list[Atom]:
    if isinstance(expr, Atom):
        return [expr]
    if isinstance(expr, Not):
        return _leaves(expr.operand)
    return [a for op in expr.operands for a in _leaves(op)]
