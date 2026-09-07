"""Benchmark arms and the shared item/prediction types.

Two arms, one cross-cutting layer:

* ``real_criteria``  — criteria segmented from the ClinicalTrials.gov snapshot.
* ``compositional``  — the depth-parameterised logic stress test.
* calibration/abstention — scored over any arm's predictions, no separate item set.
"""
from criterialogic.tasks.base import Item, Prediction, expression_depth  # noqa: F401
