# CriteriaLogic — evaluation report

## compositional  ·  negation_blind  ·  n=500
- Accuracy: **0.576** [0.532, 0.619]
- By nesting depth:
    - depth 3: 0.576 [0.532, 0.619]  (n=500)
- ECE: 0.124  ·  mean confidence: 0.700  ·  abstentions: 0
    - **no usable confidence signal**: every prediction carries the same confidence, so the selective-accuracy curve is flat at the overall accuracy and abstention cannot be evaluated.
- Failure taxonomy (labeller v2, heuristic): logical_composition=123  negation_polarity=86  numeric_threshold=1  temporal=2
- Provenance: sources=ctgov, polarities=inclusion, patients=synthetic, composition=synthetic
