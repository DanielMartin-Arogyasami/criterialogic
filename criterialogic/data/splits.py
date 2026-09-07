"""Deterministic train/test splitting with a leakage check.

Splitting is keyed on trial identifier, not on criterion, so no trial straddles the
boundary. Two criteria from the same trial share vocabulary and often share structure,
and putting one on each side of a split leaks. The check is enforced rather than
documented: :func:`split_by_trial` verifies the partition before returning it.

Nothing in v0.2 trains, so this is unused by the current arms — it is here because the
snapshot supports it and because a structuring task (docs/V2_SCOPE.md) would need it on
day one.
"""
from __future__ import annotations

import random

from criterialogic.schema.logical_form import LogicalForm
from criterialogic.schema.validators import check_no_trial_leakage


def split_by_trial(forms: list[LogicalForm], test_frac: float = 0.2, seed: int = 7,
                   key: str = "trial_id") -> tuple[list[LogicalForm], list[LogicalForm]]:
    """Group by trial id, assign whole trials to splits, then verify no leakage."""
    rng = random.Random(seed)
    trials = sorted({f.metadata.get(key, f.criterion_id) for f in forms})
    rng.shuffle(trials)
    n_test = max(1, int(len(trials) * test_frac))
    test_trials = set(trials[:n_test])
    train = [f for f in forms if f.metadata.get(key, f.criterion_id) not in test_trials]
    test = [f for f in forms if f.metadata.get(key, f.criterion_id) in test_trials]
    check_no_trial_leakage(train, test, key=key)
    return train, test
