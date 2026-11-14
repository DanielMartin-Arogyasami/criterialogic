"""structure.py — what else changes when nesting depth changes.

Depth is defined by :func:`criterialogic.tasks.base.expression_depth`: an atom has depth
0, a NOT node adds nothing, and a Boolean group has depth one more than its deepest
operand. So ``A AND B`` has depth 1 and ``A AND (B OR C)`` has depth 2.

Depth is a single number, and an item set that varies it can vary other things at the
same time: the number of predicates, the number of operators, the length of the prompt,
the share of facts left undocumented, and the base rate of the gold label. This module
counts those, so a per-depth table can show whether depth is acting as a proxy for
something else. Standard library only, like the rest of ``metrics``.
"""
from __future__ import annotations

import math

from criterialogic.oracle import PatientFacts
from criterialogic.schema.logical_form import Atom, BooleanGroup, BoolOp, Expression, Not, canonicalize
from criterialogic.tasks.base import expression_depth


def leaf_atoms(expr: Expression) -> list[Atom]:
    """Every atom in the expression, in left-to-right order, repeats included."""
    if isinstance(expr, Atom):
        return [expr]
    if isinstance(expr, Not):
        return leaf_atoms(expr.operand)
    if isinstance(expr, BooleanGroup):
        return [a for op in expr.operands for a in leaf_atoms(op)]
    raise TypeError(f"Unknown expression node: {type(expr)!r}")


def expression_stats(expr: Expression) -> dict:
    """Structural counts for one expression.

    ``canonical_depth`` is the depth after :func:`canonicalize`, which flattens a group
    nested directly inside a group with the same operator. Where it is lower than
    ``depth``, part of the nominal nesting is logically redundant.
    """
    counts = {"leaves": 0, "and_groups": 0, "or_groups": 0, "nots": 0}

    def walk(e: Expression) -> None:
        if isinstance(e, Atom):
            counts["leaves"] += 1
        elif isinstance(e, Not):
            counts["nots"] += 1
            walk(e.operand)
        elif isinstance(e, BooleanGroup):
            counts["and_groups" if e.operator is BoolOp.AND else "or_groups"] += 1
            for op in e.operands:
                walk(op)
        else:
            raise TypeError(f"Unknown expression node: {type(e)!r}")

    walk(expr)
    counts["groups"] = counts["and_groups"] + counts["or_groups"]
    counts["depth"] = expression_depth(expr)
    counts["canonical_depth"] = expression_depth(canonicalize(expr))
    return counts


def undocumented_leaves(expr: Expression, facts: PatientFacts) -> int:
    """Leaves whose entity has no fact in the record (the oracle reads these as unknown)."""
    return sum(1 for a in leaf_atoms(expr) if facts.get(a.entity.text) is None)


def currency_ambiguous_leaves(expr: Expression, facts: PatientFacts) -> int:
    """Leaves with no time qualifier whose fact is present but recorded as not current.

    The oracle counts such a leaf as satisfied, because the atom states no time
    constraint. The v2 prompt renders the fact as "present, not currently active", and
    a reader can reasonably take a present-tense criterion ("receiving X") as not met.
    The label then rests on a convention the prompt does not state.
    """
    n = 0
    for a in leaf_atoms(expr):
        f = facts.get(a.entity.text)
        if a.temporal is None and f is not None and f.present and not f.current:
            n += 1
    return n


def pearson_r(x: list[float], y: list[float]) -> float:
    """Pearson correlation. Used to show how tightly depth tracks expression size."""
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0


def balanced_accuracy(rows: list[tuple[bool, bool]]) -> float | None:
    """Mean of per-class recall over (gold, predicted) pairs; None if a class is absent.

    Accuracy alone moves with the gold base rate. A system that answers "met" for every
    item scores the met-rate, which differs by depth in the released sets; balanced
    accuracy puts that system at 0.5 regardless.
    """
    pos = [p for g, p in rows if g]
    neg = [p for g, p in rows if not g]
    if not pos or not neg:
        return None
    return 0.5 * (sum(1 for p in pos if p) / len(pos) + sum(1 for p in neg if not p) / len(neg))
