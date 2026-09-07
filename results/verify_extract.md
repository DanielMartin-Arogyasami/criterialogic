# Numbers extract for `--verify`

Checked figures: the §7.1 depth rows, Spearman rho, the permutation p, §3.2 composition,
§7.6 micro-F1 and the §7.7 accuracy range.
Generated from `results/compositional__openai.json` (`gpt-4o-mini`, prompt v2).

| Depth | Accuracy | 95% Wilson CI | Errors | ECE | Mean confidence |
|---|---|---|---|---|---|
| 2 | **0.800** | [0.682, 0.882] | 12 | 0.075 | 0.875 |
| 3 | **0.683** | [0.558, 0.787] | 19 | 0.173 | 0.857 |
| 4 | **0.517** | [0.393, 0.638] | 29 | 0.283 | 0.800 |
| 5 | **0.650** | [0.524, 0.758] | 21 | 0.142 | 0.788 |
| 6 | **0.367** | [0.256, 0.493] | 38 | 0.423 | 0.790 |

Spearman ρ = **−0.9**, exact one-sided permutation *p* = **0.0417**.

### 3.2 Data sources

§3.2 composition: **463** criteria from **219** trials.

### 7.6 Real-criteria arm

§7.6 real-criteria arm: micro-F1 **0.935**, n = 926.

### 7.7 Ablations

§7.7 ablations: a single prompt produced an accuracy range of **0.433** across depths 2–6.
