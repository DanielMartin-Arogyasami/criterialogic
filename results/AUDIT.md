# CriteriaLogic — integrity audit of `paper_data.json`

Audited results\paper_data.json · generated 2026-08-29T21:53:46+00:00

**15 HIGH · 2 MEDIUM · 5 NOTE · 3 EXPECTED (disclosed artifacts)**

> Every HIGH finding blocks a specific claim in the manuscript. Nothing below is a suggestion about presentation; each one is a place where the current data would not support the sentence the paper wants to write.

## C1 — Constant-confidence models and fabricated abstention curves

### [NOTE] `compositional_large::rule_based`

Single confidence bin; ECE here is just |accuracy - constant confidence|.

- `mean_confidence`: 0.98
- `accuracy`: 1.0
- `ece`: 0.02

**Action.** State that ECE is degenerate for this model rather than presenting it as calibration.

### [HIGH] `matching::negation_blind`

Every prediction carries the same confidence, so ranking by confidence is arbitrary, yet the reported selective-accuracy curve varies by 0.214. That variation is list order, not confidence. The curve is flat at the overall accuracy and the model has no usable abstention signal.

- `mean_confidence`: 0.7
- `accuracy`: 0.9230769230769231
- `ece`: 0.22307692307692317
- `reported_curve_spread`: 0.2143

**Action.** Do not report this curve in Sec. 7.4. Report the model as providing no confidence signal.

### [HIGH] `compositional::negation_blind`

Every prediction carries the same confidence, so ranking by confidence is arbitrary, yet the reported selective-accuracy curve varies by 0.472. That variation is list order, not confidence. The curve is flat at the overall accuracy and the model has no usable abstention signal.

- `mean_confidence`: 0.7
- `accuracy`: 0.5277777777777778
- `ece`: 0.17222222222222217
- `reported_curve_spread`: 0.4722

**Action.** Do not report this curve in Sec. 7.4. Report the model as providing no confidence signal.

### [HIGH] `compositional_large::negation_blind`

Every prediction carries the same confidence, so ranking by confidence is arbitrary, yet the reported selective-accuracy curve varies by 0.065. That variation is list order, not confidence. The curve is flat at the overall accuracy and the model has no usable abstention signal.

- `mean_confidence`: 0.7
- `accuracy`: 0.61
- `ece`: 0.08999999999999997
- `reported_curve_spread`: 0.065

**Action.** Do not report this curve in Sec. 7.4. Report the model as providing no confidence signal.

## C3 — Ceiling effects: tasks that no longer discriminate

### [EXPECTED] `matching::rule_based`

Perfect score on n=104. The 95% CI lower bound is 0.964, so this set cannot distinguish the system from one that is 96% accurate. The task does not discriminate at this size.

- `metric`: overall_micro_f1
- `value`: 1.0
- `n`: 104
- `wilson_95`: [0.9644, 1.0]
- `n_needed_to_detect_95pct`: 150
- `n_needed_to_detect_90pct`: 71

**Action.** Software-validation artifact; already disclosed.

### [EXPECTED] `compositional::rule_based`

Perfect score on n=36. The 95% CI lower bound is 0.904, so this set cannot distinguish the system from one that is 90% accurate. The task does not discriminate at this size.

- `metric`: overall_accuracy
- `value`: 1.0
- `n`: 36
- `wilson_95`: [0.9036, 1.0]
- `n_needed_to_detect_95pct`: 150
- `n_needed_to_detect_90pct`: 71

**Action.** Software-validation artifact; already disclosed.

### [EXPECTED] `compositional_large::rule_based`

Perfect score on n=400. The 95% CI lower bound is 0.990, so this set cannot distinguish the system from one that is 99% accurate. The task does not discriminate at this size.

- `metric`: overall_accuracy
- `value`: 1.0
- `n`: 400
- `wilson_95`: [0.9905, 1.0]
- `n_needed_to_detect_95pct`: 150
- `n_needed_to_detect_90pct`: 71

**Action.** Software-validation artifact; already disclosed.

### [HIGH] `compositional::openai`

Perfect score on n=36. The 95% CI lower bound is 0.904, so this set cannot distinguish the system from one that is 90% accurate. The task does not discriminate at this size.

- `metric`: overall_accuracy
- `value`: 1.0
- `n`: 36
- `wilson_95`: [0.9036, 1.0]
- `n_needed_to_detect_95pct`: 150
- `n_needed_to_detect_90pct`: 71

**Action.** Harden the task (greater depth, more operands, adversarial distractors) or enlarge n before making any claim from this row.

## C4 — Error counts vs. distinct failure modes

### [HIGH] `matching::openai`

5 error items collapse to 2 distinct rationales. These are not independent observations; one systematic misreading is replicated across items. Reporting the raw count as a taxonomy distribution overstates the evidence.

- `raw_error_count`: 5
- `distinct_rationales`: 2
- `largest_cluster`: 4
- `clusters`: [{"count": 4, "rationale": "Aspirin for myocardial infarction prophylaxis is present, indicating current/ongoing use and satisfying the criterion."}]
- `errors_per_criterion`: {"match:ALCOHOL-ABUSE": 1, "match:ASP-FOR-MI": 4}

**Action.** Report both counts in Sec. 7.3: raw errors and distinct failure modes. The taxonomy percentage must be computed over distinct modes.

## C5 — Errors that are probably item bugs, not model failures

### [HIGH] `matching::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: match:ALCOHOL-ABUSE:000
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.85
- `assigned_category`: temporal
- `rationale`: The criterion requires current/ongoing alcohol abuse; the patient has alcohol abuse present, indicating ongoing use over the limit.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `matching::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: match:ASP-FOR-MI:000
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.9
- `assigned_category`: temporal
- `rationale`: Aspirin for myocardial infarction prophylaxis is present, indicating current/ongoing use and satisfying the criterion.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `matching::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: match:ASP-FOR-MI:001
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.9
- `assigned_category`: temporal
- `rationale`: Aspirin for myocardial infarction prophylaxis is present, indicating current/ongoing use and satisfying the criterion.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `matching::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: match:ASP-FOR-MI:003
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.9
- `assigned_category`: temporal
- `rationale`: Aspirin for myocardial infarction prophylaxis is present, indicating current/ongoing use and satisfying the criterion.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `matching::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: match:ASP-FOR-MI:006
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.9
- `assigned_category`: temporal
- `rationale`: Aspirin for myocardial infarction prophylaxis is present, indicating current/ongoing use and satisfying the criterion.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

## C6 — Depth-trend statistics

### [NOTE] `compositional::rule_based`

Accuracy is monotonically non-increasing with depth.

- `depths`: [1, 2, 3]
- `accuracies`: [1.0, 1.0, 1.0]
- `n_per_depth`: [12, 12, 12]
- `wilson_95`: [[0.7575, 1.0], [0.7575, 1.0], [0.7575, 1.0]]
- `spearman_rho`: 0.0
- `exact_permutation_p`: 1.0
- `monotonic_decline`: True
- `pairwise`: [{"depths": [1, 2], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [1, 3], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [2, 3], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}]

**Action.** Report rho with the exact p-value and per-depth Wilson intervals. Where the intervals overlap, state that the depths are indistinguishable at this n and give the n-per-depth required.

### [NOTE] `compositional_large::rule_based`

Accuracy is monotonically non-increasing with depth.

- `depths`: [1, 2, 3, 4]
- `accuracies`: [1.0, 1.0, 1.0, 1.0]
- `n_per_depth`: [100, 100, 100, 100]
- `wilson_95`: [[0.963, 1.0], [0.963, 1.0], [0.963, 1.0], [0.963, 1.0]]
- `spearman_rho`: 0.0
- `exact_permutation_p`: 1.0
- `monotonic_decline`: True
- `pairwise`: [{"depths": [1, 2], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [1, 3], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [1, 4], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [2, 3], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [2, 4], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [3, 4], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}]

**Action.** Report rho with the exact p-value and per-depth Wilson intervals. Where the intervals overlap, state that the depths are indistinguishable at this n and give the n-per-depth required.

### [NOTE] `compositional::negation_blind`

Accuracy is monotonically non-increasing with depth.

- `depths`: [1, 2, 3]
- `accuracies`: [0.75, 0.5833333333333334, 0.25]
- `n_per_depth`: [12, 12, 12]
- `wilson_95`: [[0.4677, 0.9111], [0.3195, 0.8067], [0.0889, 0.5323]]
- `spearman_rho`: -1.0
- `exact_permutation_p`: 0.3333
- `monotonic_decline`: True
- `pairwise`: [{"depths": [1, 2], "accuracies": [0.75, 0.5833333333333334], "cis_overlap": true, "n_per_depth_needed": 122}, {"depths": [1, 3], "accuracies": [0.75, 0.25], "cis_overlap": true, "n_per_depth_needed": 12}, {"depths": [2, 3], "accuracies": [0.5833333333333334, 0.25], "cis_overlap": true, "n_per_depth_needed": 31}]

**Action.** Report rho with the exact p-value and per-depth Wilson intervals. Where the intervals overlap, state that the depths are indistinguishable at this n and give the n-per-depth required.

### [HIGH] `compositional_large::negation_blind`

Accuracy is NOT monotonically decreasing with depth. Sec. 7.2 states monotonic decline as the hypothesis; this run does not support it.

- `depths`: [1, 2, 3, 4]
- `accuracies`: [0.68, 0.58, 0.6, 0.58]
- `n_per_depth`: [100, 100, 100, 100]
- `wilson_95`: [[0.5834, 0.7633], [0.4821, 0.672], [0.502, 0.6906], [0.4821, 0.672]]
- `spearman_rho`: -0.6325
- `exact_permutation_p`: 0.5
- `monotonic_decline`: False
- `pairwise`: [{"depths": [1, 2], "accuracies": [0.68, 0.58], "cis_overlap": true, "n_per_depth_needed": 362}, {"depths": [1, 3], "accuracies": [0.68, 0.6], "cis_overlap": true, "n_per_depth_needed": 562}, {"depths": [1, 4], "accuracies": [0.68, 0.58], "cis_overlap": true, "n_per_depth_needed": 362}, {"depths": [2, 3], "accuracies": [0.58, 0.6], "cis_overlap": true, "n_per_depth_needed": 9490}, {"depths": [2, 4], "accuracies": [0.58, 0.58], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [3, 4], "accuracies": [0.6, 0.58], "cis_overlap": true, "n_per_depth_needed": 9490}]

**Action.** Report rho with the exact p-value and per-depth Wilson intervals. Where the intervals overlap, state that the depths are indistinguishable at this n and give the n-per-depth required.

### [NOTE] `compositional::openai`

Accuracy is monotonically non-increasing with depth.

- `depths`: [1, 2, 3]
- `accuracies`: [1.0, 1.0, 1.0]
- `n_per_depth`: [12, 12, 12]
- `wilson_95`: [[0.7575, 1.0], [0.7575, 1.0], [0.7575, 1.0]]
- `spearman_rho`: 0.0
- `exact_permutation_p`: 1.0
- `monotonic_decline`: True
- `pairwise`: [{"depths": [1, 2], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [1, 3], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}, {"depths": [2, 3], "accuracies": [1.0, 1.0], "cis_overlap": true, "n_per_depth_needed": -1}]

**Action.** Report rho with the exact p-value and per-depth Wilson intervals. Where the intervals overlap, state that the depths are indistinguishable at this n and give the n-per-depth required.

## C7 — Missing leaderboard cells

### [HIGH] `compositional_large`

Dataset 'compositional_large' was never evaluated for: openai. The leaderboard has a hole, and if this is the larger or deeper set it is precisely the cell most likely to be informative.

- `models_run`: ["negation_blind", "rule_based"]
- `models_missing`: ["openai"]

**Action.** Run openai on 'compositional_large' before drafting Sec. 7.1 or 7.2.

## C8 — Inference-parameter contradictions

### [HIGH] `matching::openai`

The per-run model record asserts a temperature that was never applied. Anyone reading the JSON (rather than the prose banner) gets a false inference parameter, which is exactly what Sec. 6 promises to report.

- `run_record_says`: {"temperature": 0.0}
- `reproducibility_says`: {"requested": 0.0, "effective": "none (API default)"}

**Action.** Replace with requested_temperature / effective_temperature / dropped_parameters recorded per call at request time.

### [HIGH] `compositional::openai`

The per-run model record asserts a temperature that was never applied. Anyone reading the JSON (rather than the prose banner) gets a false inference parameter, which is exactly what Sec. 6 promises to report.

- `run_record_says`: {"temperature": 0.0}
- `reproducibility_says`: {"requested": 0.0, "effective": "none (API default)"}

**Action.** Replace with requested_temperature / effective_temperature / dropped_parameters recorded per call at request time.

## C9 — Discrepancy list synchronisation

### [MEDIUM] `corpus-level`

The JSON carries 2 discrepancies but text inside it refers to entry 3 of results/DISCREPANCIES.md. The machine-readable list is behind the prose one, so an automated reader sees fewer known problems than exist.

- `entries_in_json`: 2
- `highest_entry_referenced`: 3

**Action.** Make DISCREPANCIES.md generated from the JSON list, not maintained beside it.

## C10 — Polarity and structural coverage

### [HIGH] `corpus-level`

All 13 matching criteria are encoded polarity=inclusion. There is no exclusion criterion anywhere in the task, so criterion-level polarity cannot be tested. Sec. 3.1 justifies keeping polarity distinct from negation in order to 'test exclusion semantics directly', and negation/polarity is taxonomy category 1.

- `polarity_distribution`: {"inclusion": 13}

**Action.** Either add exclusion-polarity items (the ClinicalTrials.gov pool has real exclusion criteria) or state plainly in Sec. 3.1 and the limitations that no released component exercises exclusion polarity in v0.1.

### [MEDIUM] `corpus-level`

10 of 13 matching criteria are single atoms at depth 0. The matching task carries almost no compositional structure, so all compositional evidence rests on the synthetic task.

- `depth_distribution`: {"0": 10, "1": 2, "2": 1}

**Action.** Say so explicitly in Sec. 3.3 rather than letting the task table imply otherwise.

## Corrected selective-accuracy curves

Recomputed tie-aware where per-item confidences were recoverable; otherwise the run is listed as needing a rerun with per-item predictions persisted.

- `matching::rule_based`: {'status': 'NOT RECOMPUTABLE — persist per_item_predictions [{item_id, confidence, correct}] and rerun this audit'}
- `compositional::rule_based`: {'status': 'NOT RECOMPUTABLE — persist per_item_predictions [{item_id, confidence, correct}] and rerun this audit'}
- `compositional_large::rule_based`: {'status': 'DEGENERATE — single confidence bin; true curve is flat', 'flat_value': 1.0}
- `matching::negation_blind`: {'status': 'DEGENERATE — single confidence bin; true curve is flat', 'flat_value': 0.9231}
- `compositional::negation_blind`: {'status': 'DEGENERATE — single confidence bin; true curve is flat', 'flat_value': 0.5278}
- `compositional_large::negation_blind`: {'status': 'DEGENERATE — single confidence bin; true curve is flat', 'flat_value': 0.61}
- `matching::openai`: {'status': 'NOT RECOMPUTABLE — persist per_item_predictions [{item_id, confidence, correct}] and rerun this audit'}
- `compositional::openai`: {'status': 'NOT RECOMPUTABLE — persist per_item_predictions [{item_id, confidence, correct}] and rerun this audit'}

## What this audit cannot see

- Per-item confidences and correctness are not stored in `paper_data.json`, only aggregates and the error subset. C1 is detected algebraically rather than recomputed. Persist per-item predictions so the corrected curve can be computed directly.
- Item text and patient records are absent, so C5 flags candidates but cannot adjudicate them.
- Nothing here validates the gold labels themselves.
