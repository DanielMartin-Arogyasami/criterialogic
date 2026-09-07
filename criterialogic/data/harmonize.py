"""The seam where each data source is mapped onto the canonical logical form.

One entrypoint per source, so the source -> schema mapping the manuscript describes is
a function a reader can open rather than prose:

- ClinicalTrials.gov criteria -> :func:`criterialogic.data.real_criteria.build_criterion_forms`
  (Arm 1), re-exported here as :func:`harmonized_real_criteria`.
- ClinicalTrials.gov atoms -> :mod:`criterialogic.data.atom_pool`, composed by
  :mod:`criterialogic.tasks.compositional` (Arm 2).

Both arms draw on the same dated snapshot. Chia and n2c2 2018 mappings were removed in
v0.2; see docs/V2_SCOPE.md for what they were and why they are deferred.
"""
from __future__ import annotations

from criterialogic.data.real_criteria import build_criterion_forms
from criterialogic.schema.logical_form import LogicalForm
from criterialogic.schema.validators import validate_corpus


def harmonized_real_criteria(**kwargs) -> list[LogicalForm]:
    """Segmented snapshot criteria as validated LogicalForms (Arm 1).

    Keyword arguments are forwarded to
    :func:`criterialogic.data.real_criteria.build_criterion_forms`.
    """
    forms, _stats = build_criterion_forms(**kwargs)
    validate_corpus(forms)
    return forms
