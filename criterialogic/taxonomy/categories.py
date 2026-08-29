"""The seven reasoning-failure categories (the paper's differentiator, spec §5)."""
from __future__ import annotations

from enum import Enum


class FailureCategory(str, Enum):
    NEGATION_POLARITY = "negation_polarity"      # exclusion treated as inclusion, or NOT dropped
    TEMPORAL = "temporal"                         # "within 6 months", "prior", "current", "ever"
    NUMERIC_THRESHOLD = "numeric_threshold"       # boundary / comparator mistakes
    LOGICAL_COMPOSITION = "logical_composition"   # wrong AND/OR/NOT scoping in compounds
    ENTITY_CONFLATION = "entity_conflation"       # clinically distinct entities confused
    IMPLICIT_KNOWLEDGE = "implicit_knowledge"     # unstated medical inference required
    FABRICATION = "fabrication"                   # invents a constraint not in the criterion
    NONE = "none"                                 # correct, or error not attributable
CATEGORY_DESCRIPTIONS = {
    FailureCategory.NEGATION_POLARITY: "Inclusion/exclusion or NOT-scope flipped.",
    FailureCategory.TEMPORAL: "Temporal window or tense reasoning error.",
    FailureCategory.NUMERIC_THRESHOLD: "Comparator or boundary value error.",
    FailureCategory.LOGICAL_COMPOSITION: "AND/OR/NOT composition resolved incorrectly.",
    FailureCategory.ENTITY_CONFLATION: "Distinct clinical entities conflated.",
    FailureCategory.IMPLICIT_KNOWLEDGE: "Failed required unstated inference.",
    FailureCategory.FABRICATION: "Asserted a constraint absent from the criterion.",
    FailureCategory.NONE: "No attributable failure.",
}
