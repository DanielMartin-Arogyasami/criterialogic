# CriteriaLogic — evaluation report

## compositional  ·  openai  ·  n=500
- Accuracy: **0.612** [0.569, 0.654]
- By nesting depth:
    - depth 3: 0.612 [0.569, 0.654]  (n=500)
- ECE: 0.223  ·  mean confidence: 0.831  ·  abstentions: 0
    - selective accuracy @30%/50%/100% coverage: 0.7246 / 0.6659 / 0.612
- Failure taxonomy (labeller v2, heuristic): logical_composition=114  negation_polarity=69  numeric_threshold=5  temporal=6
    - 194 errors span 194 distinct rationales (largest cluster 1)
- Provenance: sources=ctgov, polarities=inclusion, patients=synthetic, composition=synthetic
