# CriteriaLogic — evaluation report

## compositional  ·  negation_blind  ·  n=500
- Accuracy: **0.562** [0.518, 0.605]
- By nesting depth:
    - depth 2: 0.510 [0.413, 0.606]  (n=100)
    - depth 3: 0.650 [0.552, 0.736]  (n=100)
    - depth 4: 0.530 [0.433, 0.625]  (n=100)
    - depth 5: 0.590 [0.492, 0.681]  (n=100)
    - depth 6: 0.530 [0.433, 0.625]  (n=100)
- Depth trend: rho=0.205, p=0.667 (exact, floor 0.008); monotonic=False
    - indistinguishable at this n — (2, 3): n>=194, (2, 4): n>=9795, (2, 5): n>=606, (2, 6): n>=9795, (3, 4): n>=263, (3, 5): n>=1027, (3, 6): n>=263, (4, 5): n>=1074, (4, 6): identical, (5, 6): n>=1074
- ECE: 0.138  ·  mean confidence: 0.700  ·  abstentions: 0
    - **no usable confidence signal**: every prediction carries the same confidence, so the selective-accuracy curve is flat at the overall accuracy and abstention cannot be evaluated.
- Failure taxonomy (labeller v2, heuristic): logical_composition=103  negation_polarity=114  numeric_threshold=1  temporal=1
- Provenance: sources=ctgov, polarities=inclusion, patients=synthetic, composition=synthetic
