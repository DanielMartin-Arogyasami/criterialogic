# Paper data — generated 2026-09-12T20:33:28+00:00

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

## Section 7.5 — failure taxonomy

Heuristic labeller version(s) ['1', '2']. Heuristic triage labels. The manuscript's distribution is the human consensus; three categories are unreachable by any counterfactual over the logical form.

| Category | Pooled errors |
|---|---|
| logical_composition | 199 |
| negation_polarity | 140 |
| none | 41 |
| numeric_threshold | 6 |
| temporal | 4 |

Human-only categories, unreachable by the labeller: ['entity_conflation', 'fabrication', 'implicit_knowledge'].

**Human annotation: [not run].**

To be reported: consensus distribution [...]; Cohen's kappa [k] with 95% CI
[lo, hi]; percent agreement [x]; per-category kappa [...]; kappa by arm
(compositional [k], real criteria [k]); fraction flagged as requiring
clinical judgement [x] with kappa flagged [k] versus not [k]; disagreements
adjudicated [n], of which clinical [n]; automatic-versus-consensus kappa [k]
with [n] agreement-impossible items.

Fill with: `scripts/annotation_export.py then scripts/annotation_report.py --adjudication ...`

## Integrity gates

### [BLOCK] compositional::negation_blind

Every prediction carries the same confidence, so the selective-accuracy curve is flat at the overall accuracy and abstention cannot be evaluated.

**Action.** Report as providing no confidence signal. Do not present a curve.

### [NOTE] compositional::rule_based

Perfect score on n=240; the 95% lower bound is 0.9842, so this set cannot distinguish the system from one that is 98% accurate.

**Action.** If this is the oracle baseline, label it a software-validation artifact.

### [BLOCK] real_criteria::negation_blind

Every prediction carries the same confidence, so the selective-accuracy curve is flat at the overall accuracy and abstention cannot be evaluated.

**Action.** Report as providing no confidence signal. Do not present a curve.

### [BLOCK] real_criteria::openai

60 errors collapse to 51 distinct rationales — one systematic misreading replicated, not independent observations.

**Action.** Report both counts; compute any taxonomy percentage over distinct modes.

### [NOTE] real_criteria::rule_based

Perfect score on n=926; the 95% lower bound is 0.9959, so this set cannot distinguish the system from one that is 100% accurate.

**Action.** If this is the oracle baseline, label it a software-validation artifact.

### [BLOCK] depth sweep

Accuracy is not monotonically non-increasing with depth.

**Action.** State the observed pattern; do not assert monotonic decline.

### [NOTE] depth sweep

Smallest attainable p with 5 levels is 0.0083.

**Action.** Report the floor wherever the p-value appears.

### [NOTE] depths (2, 3)

Indistinguishable at this sample size. Separating them needs n>=220 per depth.

**Action.** Do not claim a difference between these two depths individually.

### [NOTE] depths (2, 5)

Indistinguishable at this sample size. Separating them needs n>=138 per depth.

**Action.** Do not claim a difference between these two depths individually.

### [NOTE] depths (3, 4)

Indistinguishable at this sample size. Separating them needs n>=135 per depth.

**Action.** Do not claim a difference between these two depths individually.

### [NOTE] depths (3, 5)

Indistinguishable at this sample size. Separating them needs n>=3139 per depth.

**Action.** Do not claim a difference between these two depths individually.

### [NOTE] depths (4, 5)

Indistinguishable at this sample size. Separating them needs n>=214 per depth.

**Action.** Do not claim a difference between these two depths individually.

### [NOTE] depths (4, 6)

Indistinguishable at this sample size. Separating them needs n>=171 per depth.

**Action.** Do not claim a difference between these two depths individually.

## Provenance

```json
{
  "results_dir": "results",
  "data_dir": "data",
  "runs_loaded": {
    "compositional_large::openai": "results/missing/missing_runs.json",
    "compositional_d2::openai": "results/missing/missing_runs.json",
    "compositional_d3::openai": "results/missing/missing_runs.json",
    "compositional_d4::openai": "results/missing/missing_runs.json",
    "compositional_d5::openai": "results/missing/missing_runs.json",
    "compositional_d6::openai": "results/missing/missing_runs.json",
    "compositional::negation_blind": "results/compositional__negation_blind.json",
    "compositional::openai": "results/compositional__openai.json",
    "compositional::rule_based": "results/compositional__rule_based.json",
    "real_criteria::negation_blind": "results/real_criteria__negation_blind.json",
    "real_criteria::openai": "results/real_criteria__openai.json",
    "real_criteria::rule_based": "results/real_criteria__rule_based.json",
    "compositional::openai@mixed_v2": "results/mixed_v2/compositional__openai.json"
  },
  "inference_parameters": {
    "compositional_large::openai": {
      "requested_temperature": 0.0,
      "effective_temperature": "API default \u2014 gpt-5-nano rejects a custom temperature and the adapter drops it",
      "warning": "Do not report requested temperature as if it were applied."
    },
    "compositional_d2::openai": {
      "requested_temperature": 0.0,
      "effective_temperature": "API default \u2014 gpt-5-nano rejects a custom temperature and the adapter drops it",
      "warning": "Do not report requested temperature as if it were applied."
    },
    "compositional_d3::openai": {
      "requested_temperature": 0.0,
      "effective_temperature": "API default \u2014 gpt-5-nano rejects a custom temperature and the adapter drops it",
      "warning": "Do not report requested temperature as if it were applied."
    },
    "compositional_d4::openai": {
      "requested_temperature": 0.0,
      "effective_temperature": "API default \u2014 gpt-5-nano rejects a custom temperature and the adapter drops it",
      "warning": "Do not report requested temperature as if it were applied."
    },
    "compositional_d5::openai": {
      "requested_temperature": 0.0,
      "effective_temperature": "API default \u2014 gpt-5-nano rejects a custom temperature and the adapter drops it",
      "warning": "Do not report requested temperature as if it were applied."
    },
    "compositional_d6::openai": {
      "requested_temperature": 0.0,
      "effective_temperature": "API default \u2014 gpt-5-nano rejects a custom temperature and the adapter drops it",
      "warning": "Do not report requested temperature as if it were applied."
    },
    "compositional::negation_blind": {
      "name": "negation_blind",
      "type": "NegationBlindModel"
    },
    "compositional::openai": {
      "name": "openai",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "prompt_version": "2",
      "api_key_env": "OPENAI_API_KEY",
      "requested_temperature": 0.0,
      "effective_temperature": 0.0,
      "dropped_parameters": []
    },
    "compositional::rule_based": {
      "name": "rule_based",
      "type": "RuleBasedModel"
    },
    "real_criteria::negation_blind": {
      "name": "negation_blind",
      "type": "NegationBlindModel"
    },
    "real_criteria::openai": {
      "name": "openai",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "prompt_version": "2",
      "api_key_env": "OPENAI_API_KEY",
      "requested_temperature": 0.0,
      "effective_temperature": 0.0,
      "dropped_parameters": []
    },
    "real_criteria::rule_based": {
      "name": "rule_based",
      "type": "RuleBasedModel"
    },
    "compositional::openai@mixed_v2": {
      "name": "openai",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "prompt_version": "2",
      "api_key_env": "OPENAI_API_KEY",
      "requested_temperature": 0.0,
      "effective_temperature": 0.0,
      "dropped_parameters": []
    }
  },
  "reproducibility_note": "Item sets, gold labels and prompts are deterministic. For the current gpt-4o-mini / prompt v2 run, requested temperature 0.0 was applied (dropped_parameters empty). Completions are not redistributed; the per-item predictions are the record of the run."
}
```
