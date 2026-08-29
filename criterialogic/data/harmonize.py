"""Map each source onto the harmonized schema (one entrypoint per source).
- n2c2 criteria  -> `data.n2c2_criteria.n2c2_criteria_as_logical_forms()` (public).
- Chia           -> `data.loaders.chia.load_chia_dir(...)`.
- ClinicalTrials.gov text -> parsed downstream (Task A model) or used to seed Task D.
This module is the seam where the documented source->schema mapping lives.
"""
from __future__ import annotations

from criterialogic.data.n2c2_criteria import n2c2_criteria_as_logical_forms
from criterialogic.schema.validators import validate_corpus


def harmonized_n2c2_criteria():
    forms = n2c2_criteria_as_logical_forms()
    validate_corpus(forms)
    return forms
