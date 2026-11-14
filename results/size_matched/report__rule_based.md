# CriteriaLogic — evaluation report

## compositional  ·  rule_based  ·  n=500
- Accuracy: **1.000** [0.992, 1.000]
- By nesting depth:
    - depth 2: 1.000 [0.963, 1.000]  (n=100)
    - depth 3: 1.000 [0.963, 1.000]  (n=100)
    - depth 4: 1.000 [0.963, 1.000]  (n=100)
    - depth 5: 1.000 [0.963, 1.000]  (n=100)
    - depth 6: 1.000 [0.963, 1.000]  (n=100)
- Depth trend: rho=0.000, p=1.000 (exact, floor 0.008); monotonic=True
    - indistinguishable at this n — (2, 3): identical, (2, 4): identical, (2, 5): identical, (2, 6): identical, (3, 4): identical, (3, 5): identical, (3, 6): identical, (4, 5): identical, (4, 6): identical, (5, 6): identical
- ECE: 0.013  ·  mean confidence: 0.987  ·  abstentions: 0
    - selective accuracy @30%/50%/100% coverage: 1.0 / 1.0 / 1.0
- Failure taxonomy: no scored errors
- Provenance: sources=ctgov, polarities=inclusion, patients=synthetic, composition=synthetic
