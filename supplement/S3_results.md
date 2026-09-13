# S3. Per-depth and per-item result tables

Per-depth tables below are copied from `results/paper_data.md`, which `scripts/collect_paper_data.py` recomputes from persisted per-item predictions. Per-item predictions themselves are the JSON run files listed at the end; they are not inlined. Human labels cover the 179 `gpt-4o-mini` errors only (`annotation/annotator1_labels.csv`, `annotation/annotator2_labels.csv`). Diagnostic and legacy runs have no human labels. The full agreement record is `results/agreement.json`.

# Paper data — generated 2026-09-12T20:58:18+00:00

> Every number here was produced by executing code against the released
> artifacts, and every aggregate is recomputed from persisted per-item
> predictions rather than carried forward from a stored aggregate. Bracketed
> values mark experiments that have not been run; the command that fills each
> one is given beside it. Read the integrity gates at the end before quoting
> anything.

**4 blocking finding(s), 9 note(s).** See the end of this file.

## Section 3 — dataset composition

- Snapshot `ctgov-2026-08-29`: **300 studies**, fetched 2026-08-29T20:28:40+00:00
- Sampling frame (verbatim from the manifest): `AREA[Phase]PHASE4 AND AREA[StudyType]INTERVENTIONAL AND AREA[StudyFirstPostDate]RANGE[2026-01-01,MAX]`
- Atom pool: **522 distinct atoms from 222 trials**
- Extraction matched **675 of 4869 candidate sentences (13.9%)**
- By section: {'inclusion': 204, 'exclusion': 318}
- Atom first-posted range: **2026-06-30 … 2026-08-28** (the contamination control)

### Arm 1 (real criteria)

- **463 criteria from 219 trials**
- Mapping rate: **0.1042**
- Polarity: **{'inclusion': 186, 'exclusion': 277}**
- Depth histogram: **{'0': 449, '1': 14}**
- Coordinated (compound) criteria: **14**
- Skipped by reason: {'boilerplate_phrase': 440, 'duplicate_of_earlier_trial': 127, 'length_out_of_range': 598, 'no_faithful_mapping': 2817}

## Section 7.1 — accuracy versus logical nesting depth

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

## Section 7.2 — the mixed-depth set

**Current run.** `gpt-4o-mini`, prompt v2, source `results/mixed_v2/compositional__openai.json`.

| Depth | Accuracy | 95% Wilson CI | n |
|---|---|---|---|
| 1 | 0.780 | [0.689, 0.850] | 100 |
| 2 | 0.770 | [0.678, 0.842] | 100 |
| 3 | 0.650 | [0.552, 0.736] | 100 |
| 4 | 0.490 | [0.394, 0.587] | 100 |

Overall **0.672** [0.625, 0.717] on n=400.
Spearman rho = -1.0, exact p = 0.0417. CI-separated pairs: [(1, 4), (2, 4)].

## Section 7.3 — exposure to the renderer defect

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

## Section 7.4 — calibration and abstention

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

## Per-item prediction files

- `results/compositional__openai.json`
- `results/real_criteria__openai.json`
- `results/mixed_v2/compositional__openai.json`
- `results/compositional__rule_based.json`
- `results/compositional__negation_blind.json`
- `results/real_criteria__rule_based.json`
- `results/real_criteria__negation_blind.json`

## Human labels (`gpt-4o-mini` errors only)

- `annotation/annotator1_labels.csv` (179 rows)
- `annotation/annotator2_labels.csv` (179 rows)

- `results/agreement.json` (Cohen's κ and the rest of §7.5)
