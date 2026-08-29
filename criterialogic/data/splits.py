"""Deterministic train/test splitting with a leakage check.
Splits are seeded (reproducible). For Chia-derived data, splitting is keyed on
trial id so no trial straddles the train/test boundary (prevents contamination).
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
