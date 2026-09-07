"""Arm 1 task — decide met / not-met for a (real criterion, patient) pair.

The criteria are real: segmented verbatim from the dated ClinicalTrials.gov snapshot,
carrying the polarity of the section they came from. The patients are synthetic, and
that is the honest limit of this arm — it measures whether a system resolves a real
criterion's structure against a stated record, not whether it can find the evidence in
a real clinical note. Arm 1 is the realism check on Arm 2, not a substitute for
evaluation against real longitudinal records; the manuscript says so in Limitations,
and matching against real records is named as the main v2 extension.

Patient generation is seeded and shared with the compositional arm
(:mod:`criterialogic.data.synthetic`), so facts are sampled near constraint boundaries
rather than uniformly — an item set where every numeric threshold is missed by a mile
would measure nothing.
"""
from __future__ import annotations

import random

from criterialogic.data.synthetic import make_patient_for_criterion
from criterialogic.oracle import is_met
from criterialogic.schema.logical_form import LogicalForm
from criterialogic.tasks.base import Item, expression_depth

TASK_NAME = "real_criteria"


def generate_real_criteria_items(
    forms: list[LogicalForm],
    n_per_criterion: int = 2,
    seed: int = 17,
) -> list[Item]:
    """Pair each criterion with ``n_per_criterion`` synthetic patients.

    The gold label is the oracle's three-valued verdict collapsed with unknown -> not
    met, which is the convention the prompt states to the model. ``group`` is the source
    trial, so the per-group breakdown answers "does this system fail on particular
    trials' criteria" rather than only reporting a single pooled figure.
    """
    rng = random.Random(seed)
    items: list[Item] = []
    for form in forms:
        trial = form.metadata.get("trial_id", form.criterion_id)
        for i in range(n_per_criterion):
            record_id = f"{form.criterion_id}-P{i:02d}"
            facts = make_patient_for_criterion(form, record_id, rng)
            items.append(Item(
                item_id=f"real:{form.criterion_id}:{i:02d}",
                task=TASK_NAME,
                criterion=form,
                facts=facts,
                gold=is_met(form, facts),
                group=trial,
                depth=expression_depth(form.expression),
            ))
    return items
