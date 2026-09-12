# CriteriaLogic — evaluation report

## compositional  ·  openai  ·  n=400
- Accuracy: **0.672** [0.625, 0.717]
- By nesting depth:
    - depth 1: 0.780 [0.689, 0.850]  (n=100)
    - depth 2: 0.770 [0.678, 0.842]  (n=100)
    - depth 3: 0.650 [0.552, 0.736]  (n=100)
    - depth 4: 0.490 [0.394, 0.587]  (n=100)
- Depth trend: rho=-1.000, p=0.042 (exact, floor 0.042); monotonic=True
    - indistinguishable at this n — (1, 2): n>=27372, (1, 3): n>=189, (2, 3): n>=224, (3, 4): n>=150
- ECE: 0.188  ·  mean confidence: 0.860  ·  abstentions: 0
    - selective accuracy @30%/50%/100% coverage: 0.7803 / 0.7668 / 0.6725
- Failure taxonomy (labeller v2, heuristic): logical_composition=51  negation_polarity=68  numeric_threshold=8  temporal=4
    - 131 errors span 131 distinct rationales (largest cluster 1)
- Provenance: sources=ctgov, polarities=inclusion, patients=synthetic, composition=synthetic
