"""The size-matched set: depth varies, and nothing that the reviewers named varies with it."""
import json

import pytest

from criterialogic.metrics.structure import expression_stats
from criterialogic.tasks.size_matched import _check_params, generate_size_matched_items


@pytest.fixture(scope="module")
def items():
    return generate_size_matched_items(depths=(2, 3, 4, 5, 6), n_per_depth=20, seed=7)


def test_structure_is_fixed_across_depth(items):
    for it in items:
        s = expression_stats(it.criterion.expression)
        assert s["leaves"] == 14 and s["groups"] == 6 and s["nots"] == 4
        assert s["depth"] == it.depth
        assert s["canonical_depth"] == it.depth, "no level may be flattened away"


def test_gold_is_balanced_within_each_depth(items):
    for d in (2, 3, 4, 5, 6):
        golds = [it.gold for it in items if it.depth == d]
        assert len(golds) == 20 and sum(golds) == 10


def test_and_or_alternate_along_every_path(items):
    def check(e, parent_op=None):
        kind = e.node_type
        if kind == "atom":
            return
        if kind == "not":
            return check(e.operand, parent_op)
        assert e.operator != parent_op
        for op in e.operands:
            check(op, e.operator)
    for it in items:
        check(it.criterion.expression)


def test_generation_is_deterministic():
    a = generate_size_matched_items(depths=(2, 4), n_per_depth=6, seed=3)
    b = generate_size_matched_items(depths=(2, 4), n_per_depth=6, seed=3)
    c = generate_size_matched_items(depths=(2, 4), n_per_depth=6, seed=4)
    dump = lambda xs: json.dumps([x.model_dump(mode="json") for x in xs])  # noqa: E731
    assert dump(a) == dump(b) and dump(a) != dump(c)


@pytest.mark.parametrize("leaves,groups,nots,depths", [
    (14, 6, 4, [7]),        # deeper than the number of groups allows
    (14, 6, 4, [1]),        # depth 1 is a single group
    (8, 6, 4, [3]),         # too few leaves for a star of six groups
    (14, 6, 30, [3]),       # more NOTs than nodes
])
def test_impossible_parameters_are_refused(leaves, groups, nots, depths):
    with pytest.raises(ValueError):
        _check_params(leaves, groups, nots, depths)


# --------------------------------------------------------------------------- #
# The converse design: size varies at fixed depth
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def sweep():
    from criterialogic.tasks.size_matched import generate_size_sweep_items
    return generate_size_sweep_items(n_per_size=10, seed=5)


def test_size_sweep_holds_depth_and_scales_size(sweep):
    from criterialogic.tasks.size_matched import DEFAULT_SWEEP_SIZES
    by_leaves = {}
    for it in sweep:
        s = expression_stats(it.criterion.expression)
        assert s["depth"] == 3 and s["canonical_depth"] == 3 and it.depth == 3
        by_leaves.setdefault(s["leaves"], []).append((s["groups"], s["nots"], it.gold))
    assert sorted(by_leaves) == [a for a, _, _ in DEFAULT_SWEEP_SIZES]
    for leaves, groups, nots in DEFAULT_SWEEP_SIZES:
        rows = by_leaves[leaves]
        assert all(g == groups and n == nots for g, n, _ in rows)
        assert len(rows) == 10 and sum(1 for *_, gold in rows if gold) == 5


def test_size_sweep_ids_are_unique_and_deterministic(sweep):
    from criterialogic.tasks.size_matched import generate_size_sweep_items
    assert len({it.item_id for it in sweep}) == len(sweep)
    again = generate_size_sweep_items(n_per_size=10, seed=5)
    assert [x.model_dump(mode="json") for x in again] == [x.model_dump(mode="json") for x in sweep]


def test_size_matched_released_set_is_unchanged_by_the_shared_helper():
    # Guards the refactor that added the size sweep: the committed size-matched item set
    # must still regenerate byte-for-byte from the default arguments.
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data/processed/logic_set_size_matched.json"
    if not path.is_file():
        pytest.skip("size-matched item set not generated in this checkout")
    # The pool digest is a hash of the pool file's bytes, so a checkout that converts it to
    # CRLF stamps a different digest on otherwise identical items; compare without it.
    def strip(rows):
        for r in rows:
            r["criterion"]["metadata"].pop("atom_pool_sha256", None)
        return rows
    regenerated = strip([it.model_dump(mode="json") for it in generate_size_matched_items()])
    committed = strip(json.loads(path.read_text(encoding="utf-8")))
    assert regenerated == committed
