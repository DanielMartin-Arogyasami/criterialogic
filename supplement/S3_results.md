# S3. Per-level and per-item result tables

The per-depth and calibration tables of the original runs, with the collector's integrity gates, are copied from `results/paper_data.md`, which `scripts/collect_paper_data.py` recomputes from persisted per-item predictions; their section numbers follow the revised manuscript. The tables added in revision follow them: for each of the four compositional item sets, the structure of every level (leaves, AND/OR/NOT counts, undocumented leaves, prompt length, gold and model met rates) with its accuracy and the item-level trend; and the real-criteria arm on the verified subsets. Per-item predictions themselves are the JSON run files listed at the end; they are not inlined. Human labels cover the 179 `gpt-4o-mini` errors only (`annotation/annotator1_labels.csv`, `annotation/annotator2_labels.csv`). Diagnostic and legacy runs have no human labels. The full agreement record is `results/agreement.json`.

## Paper data — generated 2026-09-12T20:58:18+00:00

> Every number here was produced by executing code against the released
> artifacts, and every aggregate is recomputed from persisted per-item
> predictions rather than carried forward from a stored aggregate. Bracketed
> values mark experiments that have not been run; the command that fills each
> one is given beside it. Read the integrity gates below before quoting
> anything.

**4 blocking finding(s), 9 note(s).** See the integrity gates below.

### Section 3.2 — dataset composition

- Snapshot `ctgov-2026-08-29`: **300 studies**, fetched 2026-08-29T20:28:40+00:00
- Sampling frame (verbatim from the manifest): `AREA[Phase]PHASE4 AND AREA[StudyType]INTERVENTIONAL AND AREA[StudyFirstPostDate]RANGE[2026-01-01,MAX]`
- Atom pool: **522 distinct atoms from 222 trials**
- Extraction matched **675 of 4869 candidate sentences (13.9%)**
- By section: {'inclusion': 204, 'exclusion': 318}
- Atom first-posted range: **2026-06-30 … 2026-08-28** (the contamination control)

#### Arm 1 (real criteria)

- **463 criteria from 219 trials**
- Mapping rate: **0.1042**
- Polarity: **{'inclusion': 186, 'exclusion': 277}**
- Depth histogram: **{'0': 449, '1': 14}**
- Coordinated (compound) criteria: **14**
- Skipped by reason: {'boilerplate_phrase': 440, 'duplicate_of_earlier_trial': 127, 'length_out_of_range': 598, 'no_faithful_mapping': 2817}

### Section 4.1 — accuracy versus logical nesting depth

| Depth | Seed | Accuracy | 95% Wilson CI | Errors | ECE | Mean confidence | Model |
|---|---|---|---|---|---|---|---|
| 2 | 29 | **0.800** | [0.682, 0.882] | 12 | 0.075 | 0.875 | gpt-4o-mini |
| 3 | 29 | **0.683** | [0.558, 0.787] | 19 | 0.173 | 0.857 | gpt-4o-mini |
| 4 | 29 | **0.517** | [0.393, 0.638] | 29 | 0.283 | 0.800 | gpt-4o-mini |
| 5 | 29 | **0.650** | [0.524, 0.758] | 21 | 0.142 | 0.788 | gpt-4o-mini |
| 6 | 29 | **0.367** | [0.256, 0.493] | 38 | 0.423 | 0.790 | gpt-4o-mini |

Pooled: 181/300 = **0.603** [0.547, 0.657].
Spearman rho = **-0.9**, exact one-sided permutation p = **0.0417** over 120 orderings (floor 0.0083).
Monotonically non-increasing: **False**.
CI-separated pairs: [(2, 4), (2, 6), (3, 6), (5, 6)].
Overlapping pairs and the per-depth n that would separate them: (2, 3) n>=220, (2, 5) n>=138, (3, 4) n>=135, (3, 5) n>=3139, (4, 5) n>=214, (4, 6) n>=171.

### Section 4.1 — the mixed-depth set

**Current run.** `gpt-4o-mini`, prompt v2, source `results/mixed_v2/compositional__openai.json`.

| Depth | Accuracy | 95% Wilson CI | n |
|---|---|---|---|
| 1 | 0.780 | [0.689, 0.850] | 100 |
| 2 | 0.770 | [0.678, 0.842] | 100 |
| 3 | 0.650 | [0.552, 0.736] | 100 |
| 4 | 0.490 | [0.394, 0.587] | 100 |

Overall **0.672** [0.625, 0.717] on n=400.
Spearman rho = -1.0, exact p = 0.0417. CI-separated pairs: [(1, 4), (2, 4)].

### Appendix B.4 — exposure to the renderer defect

Source: persisted per-item flags.

| Set | Exposed n | Errors in exposed | Unexposed n | Unexposed accuracy | 95% CI |
|---|---|---|---|---|---|
| compositional::negation_blind | 0 | 0 | 240 | 0.600 | [0.537, 0.660] |
| compositional | 0 | 0 | 300 | 0.603 | [0.547, 0.657] |
| compositional::rule_based | 0 | 0 | 240 | 1.000 | [0.984, 1.000] |
| real_criteria::negation_blind | 0 | 0 | 926 | 0.970 | [0.957, 0.979] |
| real_criteria | 0 | 0 | 926 | 0.935 | [0.917, 0.949] |
| real_criteria::rule_based | 0 | 0 | 926 | 1.000 | [0.996, 1.000] |
| compositional@mixed_v2 | 0 | 0 | 400 | 0.672 | [0.625, 0.717] |

### Section 4.4 — calibration and abstention

| Set | ECE | Mean conf. | @10% | @30% | @50% | @100% | Usable signal |
|---|---|---|---|---|---|---|---|
| compositional_large::openai *(legacy)* | 0.139 | 0.781 | 0.9828 | 0.9833 | 0.9768 | 0.92 | yes |
| compositional_d2::openai *(legacy)* | 0.144 | 0.811 | 1.0 | 0.9861 | 0.9333 | 0.95 | yes |
| compositional_d3::openai *(legacy)* | 0.170 | 0.780 | 1.0 | 1.0 | 1.0 | 0.95 | yes |
| compositional_d4::openai *(legacy)* | 0.135 | 0.732 | 1.0 | 0.9778 | 0.9 | 0.8667 | yes |
| compositional_d5::openai *(legacy)* | 0.140 | 0.684 | 1.0 | 0.9167 | 0.7889 | 0.7167 | yes |
| compositional_d6::openai *(legacy)* | 0.122 | 0.659 | 0.8333 | 0.6667 | 0.6667 | 0.6 | yes |
| compositional::negation_blind | 0.100 | 0.700 | 0.6 | 0.6 | 0.6 | 0.6 | **no** |
| compositional::openai | 0.219 | 0.822 | 0.7926 | 0.7643 | 0.6747 | 0.6033 | yes |
| compositional::rule_based | 0.019 | 0.981 | 1.0 | 1.0 | 1.0 | 1.0 | yes |
| real_criteria::negation_blind | 0.270 | 0.700 | 0.9698 | 0.9698 | 0.9698 | 0.9698 | **no** |
| real_criteria::openai | 0.048 | 0.889 | 0.995 | 0.9781 | 0.9608 | 0.9352 | yes |
| real_criteria::rule_based | 0.029 | 0.971 | 1.0 | 1.0 | 1.0 | 1.0 | yes |
| compositional::openai@mixed_v2 | 0.188 | 0.860 | 0.8479 | 0.7803 | 0.7668 | 0.6725 | yes |

### Integrity gates

The collector's reporting rules for the original runs. A [BLOCK] names a way a figure must not be reported, not a failed computation.

#### [BLOCK] compositional::negation_blind

Every prediction carries the same confidence, so the selective-accuracy curve is flat at the overall accuracy and abstention cannot be evaluated.

**Action.** Report as providing no confidence signal. Do not present a curve.

#### [NOTE] compositional::rule_based

Perfect score on n=240; the 95% lower bound is 0.9842, so this set cannot distinguish the system from one that is 98% accurate.

**Action.** If this is the oracle baseline, label it a software-validation artifact.

#### [BLOCK] real_criteria::negation_blind

Every prediction carries the same confidence, so the selective-accuracy curve is flat at the overall accuracy and abstention cannot be evaluated.

**Action.** Report as providing no confidence signal. Do not present a curve.

#### [BLOCK] real_criteria::openai

60 errors collapse to 51 distinct rationales — one systematic misreading replicated, not independent observations.

**Action.** Report both counts; compute any taxonomy percentage over distinct modes.

#### [NOTE] real_criteria::rule_based

Perfect score on n=926; the 95% lower bound is 0.9959, so this set cannot distinguish the system from one that is 100% accurate.

**Action.** If this is the oracle baseline, label it a software-validation artifact.

#### [BLOCK] depth sweep

Accuracy is not monotonically non-increasing with depth.

**Action.** State the observed pattern; do not assert monotonic decline.

#### [NOTE] depth sweep

Smallest attainable p with 5 levels is 0.0083.

**Action.** Report the floor wherever the p-value appears.

#### [NOTE] depths (2, 3)

Indistinguishable at this sample size. Separating them needs n>=220 per depth.

**Action.** Do not claim a difference between these two depths individually.

#### [NOTE] depths (2, 5)

Indistinguishable at this sample size. Separating them needs n>=138 per depth.

**Action.** Do not claim a difference between these two depths individually.

#### [NOTE] depths (3, 4)

Indistinguishable at this sample size. Separating them needs n>=135 per depth.

**Action.** Do not claim a difference between these two depths individually.

#### [NOTE] depths (3, 5)

Indistinguishable at this sample size. Separating them needs n>=3139 per depth.

**Action.** Do not claim a difference between these two depths individually.

#### [NOTE] depths (4, 5)

Indistinguishable at this sample size. Separating them needs n>=214 per depth.

**Action.** Do not claim a difference between these two depths individually.

#### [NOTE] depths (4, 6)

Indistinguishable at this sample size. Separating them needs n>=171 per depth.

**Action.** Do not claim a difference between these two depths individually.

## Per-depth structure of the original depth sweep and mixed set

Source: `results/depth_structure.md`.

Generated by `scripts/depth_structure.py` from released item sets and per-item predictions.
Prompt length is the rendered user message in characters (the system prompt is constant).
Currency-ambiguous leaves: no time qualifier, fact present but recorded as not current; the oracle counts them as met.

### Depth sweep (depths 2-6, 60 per depth)

Model: gpt-4o-mini (prompt v2); n = 300.

| Depth | n | Leaves mean (range) | AND | OR | NOT | Canonical depth | Undocumented leaves | Currency-ambiguous leaves | Prompt chars | Gold met | Model says met | Accuracy [95% CI] | Balanced accuracy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 60 | 5.2 (4-8) | 1.7 | 1.6 | 2.0 | 1.88 | 1.0 | 2.4 | 551 | 0.58 | 0.52 | 0.800 [0.682, 0.882] | 0.806 |
| 3 | 60 | 12.3 (8-20) | 4.3 | 4.3 | 4.4 | 2.78 | 2.2 | 5.9 | 1,145 | 0.47 | 0.72 | 0.683 [0.558, 0.787] | 0.699 |
| 4 | 60 | 28.7 (17-44) | 10.3 | 10.5 | 10.3 | 3.73 | 3.9 | 14.2 | 2,460 | 0.53 | 0.78 | 0.517 [0.393, 0.638] | 0.498 |
| 5 | 60 | 71.8 (39-115) | 26.4 | 26.3 | 27.0 | 4.77 | 9.0 | 36.2 | 5,698 | 0.52 | 0.83 | 0.650 [0.524, 0.758] | 0.639 |
| 6 | 60 | 152.5 (96-255) | 57.1 | 56.6 | 54.4 | 5.73 | 18.1 | 74.1 | 11,167 | 0.40 | 0.97 | 0.367 [0.256, 0.493] | 0.458 |

Item-level trend over depth: odds ratio per depth level 0.675 [0.567, 0.804], likelihood-ratio p = 5.3e-06; permutation p for a decline = 5e-05 (20,000 permutations, floor 5e-05).
Item-level correlation between depth and log2(leaves): r = 0.981.

### Mixed set (depths 1-4, 100 per depth)

Model: gpt-4o-mini (prompt v2); n = 400.

| Depth | n | Leaves mean (range) | AND | OR | NOT | Canonical depth | Undocumented leaves | Currency-ambiguous leaves | Prompt chars | Gold met | Model says met | Accuracy [95% CI] | Balanced accuracy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100 | 2.3 (2-3) | 0.6 | 0.4 | 0.7 | 1.0 | 0.4 | 1.0 | 331 | 0.46 | 0.42 | 0.780 [0.689, 0.850] | 0.775 |
| 2 | 100 | 5.2 (4-8) | 1.5 | 1.8 | 1.9 | 1.82 | 0.9 | 2.4 | 583 | 0.54 | 0.55 | 0.770 [0.678, 0.842] | 0.768 |
| 3 | 100 | 13.2 (8-21) | 4.5 | 4.6 | 4.8 | 2.77 | 2.3 | 6.1 | 1,228 | 0.45 | 0.50 | 0.650 [0.552, 0.736] | 0.652 |
| 4 | 100 | 29.7 (17-51) | 10.8 | 10.6 | 10.8 | 3.79 | 4.8 | 13.9 | 2,564 | 0.42 | 0.81 | 0.490 [0.394, 0.587] | 0.541 |

Item-level trend over depth: odds ratio per depth level 0.627 [0.514, 0.764], likelihood-ratio p = 1.9e-06; permutation p for a decline = 5e-05 (20,000 permutations, floor 5e-05).
Item-level correlation between depth and log2(leaves): r = 0.973.

## Size-matched set: depth varies at 14 leaves

Source: `results/size_matched/structure__openai.md`.

Generated by `scripts/depth_structure.py` from released item sets and per-item predictions.
Prompt length is the rendered user message in characters (the system prompt is constant).
Currency-ambiguous leaves: no time qualifier, fact present but recorded as not current; the oracle counts them as met.

### Size-matched set: openai

Model: gpt-4o-mini (prompt v2); n = 500.

| Depth | n | Leaves mean (range) | AND | OR | NOT | Canonical depth | Undocumented leaves | Currency-ambiguous leaves | Prompt chars | Gold met | Model says met | Accuracy [95% CI] | Balanced accuracy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 100 | 14.0 (14-14) | 3.0 | 3.0 | 4.0 | 2.0 | 2.4 | 6.2 | 1,283 | 0.50 | 0.68 | 0.720 [0.625, 0.799] | 0.720 |
| 3 | 100 | 14.0 (14-14) | 2.9 | 3.1 | 4.0 | 3.0 | 2.3 | 6.5 | 1,294 | 0.50 | 0.65 | 0.710 [0.615, 0.790] | 0.710 |
| 4 | 100 | 14.0 (14-14) | 3.0 | 3.0 | 4.0 | 4.0 | 2.6 | 6.3 | 1,269 | 0.50 | 0.67 | 0.650 [0.552, 0.736] | 0.650 |
| 5 | 100 | 14.0 (14-14) | 2.9 | 3.1 | 4.0 | 5.0 | 2.5 | 5.9 | 1,306 | 0.50 | 0.68 | 0.660 [0.563, 0.745] | 0.660 |
| 6 | 100 | 14.0 (14-14) | 3.0 | 3.0 | 4.0 | 6.0 | 2.4 | 6.3 | 1,301 | 0.50 | 0.72 | 0.700 [0.604, 0.781] | 0.700 |

Item-level trend over depth: odds ratio per depth level 0.959 [0.839, 1.096], likelihood-ratio p = 0.54; permutation p for a decline = 0.28 (20,000 permutations, floor 5e-05).
Item-level correlation between depth and log2(leaves): r = 0.000.

## Fixed-depth size sweep: size varies at depth 3

Source: `results/size_sweep/structure__openai.md`.

Generated by `scripts/run_size_sweep.py`. Depth is held fixed; leaves, groups and NOT nodes
grow together; the gold label is half met at every size.

### Fixed-depth size sweep: openai

Model: gpt-4o-mini (prompt v2); n = 500.

| Leaves | n | Depth | AND | OR | NOT | Canonical depth | Undocumented leaves | Currency-ambiguous leaves | Prompt chars | Gold met | Model says met | Accuracy [95% CI] | Balanced accuracy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 7 | 100 | 3.0 | 1.5 | 1.5 | 2.0 | 3.0 | 1.3 | 3.0 | 721 | 0.50 | 0.64 | 0.700 [0.604, 0.781] | 0.700 |
| 14 | 100 | 3.0 | 3.0 | 3.0 | 4.0 | 3.0 | 2.3 | 6.4 | 1,295 | 0.50 | 0.67 | 0.670 [0.573, 0.754] | 0.670 |
| 28 | 100 | 3.0 | 6.2 | 5.8 | 8.0 | 3.0 | 4.5 | 12.9 | 2,391 | 0.50 | 0.80 | 0.580 [0.482, 0.672] | 0.580 |
| 56 | 100 | 3.0 | 12.1 | 11.9 | 16.0 | 3.0 | 8.7 | 25.5 | 4,521 | 0.50 | 0.86 | 0.580 [0.482, 0.672] | 0.580 |
| 112 | 100 | 3.0 | 23.6 | 24.4 | 32.0 | 3.0 | 16.8 | 53.0 | 8,689 | 0.50 | 0.89 | 0.530 [0.433, 0.625] | 0.530 |

Item-level trend over size: odds ratio per doubling of leaves 0.833 [0.732, 0.948], likelihood-ratio p = 0.0052; permutation p for a decline = 0.0024 (20,000 permutations, floor 5e-05).

## Real-criteria arm on the verified subsets

Source: `results/real_criteria_verified.md`.

Generated by `scripts/rescore_real_criteria.py` from the released predictions; no model calls.
Criteria kept: 337 of 463.

| Subset | Items | Criteria | Trials | Errors | Accuracy [95% CI] | Macro-F1 | Balanced acc. | Gold met | Model met | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| All items (released figure) | 926 | 463 | 219 | 60 | 0.935 [0.917, 0.949] | 0.935 | 0.938 | 0.544 | 0.503 | 0.048 |
| Verified criteria | 674 | 337 | 194 | 28 | 0.959 [0.941, 0.971] | 0.958 | 0.960 | 0.556 | 0.541 | 0.069 |
| Verified criteria, no currency-convention items (headline) | 376 | 238 | 156 | 13 | 0.965 [0.942, 0.980] | 0.961 | 0.964 | 0.335 | 0.343 | 0.103 |

### Inter-annotator agreement

| Error set | n | Cohen's kappa [95% CI] | Real criteria (n, kappa) | Compositional (n, kappa) |
|---|---|---|---|---|
| All 179 errors (released) | 179 | 0.337 [0.252, 0.420] | 60, 0.539 | 119, 0.088 |
| Arm 1 errors outside the headline subset removed | 132 | 0.165 [0.068, 0.266] | 13, 0.495 | 119, 0.088 |

## Power of the size-matched design, and a size-only model

Source: `results/size_checks.md`.

Generated by `scripts/size_checks.py` from released item sets and per-item predictions.

### Power of the size-matched design against the original depth effect

Original depth sweep, item-level odds ratio per depth level: 0.6753. Simulated design: depths 2-6, 100 items per depth, centred on the size-matched set's pooled accuracy (0.688); 1,000 replicates, seed 0.

Detected (likelihood-ratio p < alpha with an odds ratio below 1, alpha 0.05): 1,000 of 1,000 replicates (power 1.000).

### A model of correctness on log2(leaves) alone

Fitted to the 700 items of the original depth sweep and mixed set, with no depth term: odds ratio per doubling of leaves 0.7377.

| Leaves | Predicted accuracy | Observed in the size sweep | n |
|---|---|---|---|
| 7 | 0.716 | 0.700 | 100 |
| 14 | 0.650 | 0.670 | 100 |
| 28 | 0.578 | 0.580 | 100 |
| 56 | 0.503 | 0.580 | 100 |
| 112 | 0.427 | 0.530 | 100 |

## Item sets

- `data/processed/logic_set_depth_sweep.json`
- `data/processed/logic_set_mixed.json`
- `data/processed/logic_set_size_matched.json`
- `data/processed/logic_set_size_sweep.json`

## Per-item prediction files

- `results/compositional__openai.json`
- `results/real_criteria__openai.json`
- `results/mixed_v2/compositional__openai.json`
- `results/size_matched/compositional__openai.json`
- `results/size_sweep/compositional__openai.json`
- `results/compositional__rule_based.json`
- `results/compositional__negation_blind.json`
- `results/real_criteria__rule_based.json`
- `results/real_criteria__negation_blind.json`
- `results/size_matched/compositional__rule_based.json`
- `results/size_matched/compositional__negation_blind.json`
- `results/size_sweep/compositional__rule_based.json`
- `results/size_sweep/compositional__negation_blind.json`

## Human labels (`gpt-4o-mini` errors only)

- `annotation/annotator1_labels.csv` (179 rows)
- `annotation/annotator2_labels.csv` (179 rows)

- `results/agreement.json` (Cohen's κ and the rest of Section 4.6)
