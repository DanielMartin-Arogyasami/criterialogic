# CriteriaLogic — evaluation report

## compositional  ·  openai  ·  n=500
- Accuracy: **0.688** [0.646, 0.727]
- By nesting depth:
    - depth 2: 0.720 [0.625, 0.799]  (n=100)
    - depth 3: 0.710 [0.615, 0.790]  (n=100)
    - depth 4: 0.650 [0.552, 0.736]  (n=100)
    - depth 5: 0.660 [0.563, 0.745]  (n=100)
    - depth 6: 0.700 [0.604, 0.781]  (n=100)
- Depth trend: rho=-0.600, p=0.175 (exact, floor 0.008); monotonic=False
    - indistinguishable at this n — (2, 3): n>=31987, (2, 4): n>=691, (2, 5): n>=932, (2, 6): n>=8080, (3, 4): n>=948, (3, 5): n>=1354, (3, 6): n>=32647, (4, 5): n>=35472, (4, 6): n>=1377, (5, 6): n>=2134
- ECE: 0.174  ·  mean confidence: 0.862  ·  abstentions: 0
    - selective accuracy @30%/50%/100% coverage: 0.7264 / 0.7264 / 0.688
- Failure taxonomy (labeller v2, heuristic): logical_composition=65  negation_polarity=82  numeric_threshold=7  temporal=2
    - 156 errors span 156 distinct rationales (largest cluster 1)
- Provenance: sources=ctgov, polarities=inclusion, patients=synthetic, composition=synthetic
