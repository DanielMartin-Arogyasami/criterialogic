# CriteriaLogic — integrity audit of `paper_data.json`

Audited results\missing\missing_runs.json · generated 2026-08-29T21:53:46+00:00

**9 HIGH · 0 MEDIUM · 0 NOTE · 0 EXPECTED (disclosed artifacts)**

> Every HIGH finding blocks a specific claim in the manuscript. Nothing below is a suggestion about presentation; each one is a place where the current data would not support the sentence the paper wants to write.

## C1 — Constant-confidence models and fabricated abstention curves

No findings.

## C3 — Ceiling effects: tasks that no longer discriminate

No findings.

## C4 — Error counts vs. distinct failure modes

No findings.

## C5 — Errors that are probably item bugs, not model failures

### [HIGH] `compositional_large::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d1:044
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.62
- `assigned_category`: None
- `rationale`: Since 'following conditions will be excluded' is present (true) and BMI >= 35 is undocumented (assumed false), the conjunction is false and the NOT of it is true, so the criterion is satisfied.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `compositional_large::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d2:024
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.58
- `assigned_category`: None
- `rationale`: The criterion requires (intracranial hemorrhage OR systemic corticosteroids) and NOT hemochromatosis AND three antihypertensive medications AND PCP/ketamine abuse; the patient has intracranial hemorrhage and three antihypertensive meds, and we assume undocumented hemochromatosis is not present and PCP/ketamine abuse is present, so all conditions hold and the criterion is satisfied.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `compositional_large::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d2:063
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.62
- `assigned_category`: None
- `rationale`: A evaluates to False since egfr < 45.0 is false (47.07) and ldl-c >= 12.0 is undocumented and assumed not satisfied; B is True because suspected and concurrent croup are present; therefore A AND B is False, and NOT(False) makes the criterion satisfied.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `compositional_large::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d4:009
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.72
- `assigned_category`: None
- `rationale`: The inclusion criterion is a disjunction NOT(A1) OR NOT(A2); A1 is false because epilepsy surgery is present (NOT epilepsy is false) and age 16.44 with BMI 40.2 fail, making NOT(A1) true, so the overall criterion is satisfied regardless of A2.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `compositional_d2::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d2:012
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.86
- `assigned_category`: None
- `rationale`: All parts of the inclusion criterion are satisfied: drug-induced psoriasis is current, CNS depressants within 3 months, antibiotic within 3 months, and no excluded conditions are present.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `compositional_d2::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d2:018
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.56
- `assigned_category`: None
- `rationale`: Because hiv is negative, A ∧ hiv is false; dialysis is present, so NOT(dialysis) is false; assuming undocumented risk factors for malignancy and age 18–55 are absent yields B = R ∨ AgeInRange ∨ NOT Dialysis = false, hence NOT B is true and the inclusion criterion is satisfied.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `compositional_d4::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d4:050
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.72
- `assigned_category`: None
- `rationale`: The right-hand branch of the criterion is satisfied because 'and/or physical examination (current / ongoing)' is present, making that OR-subelement true and thus fulfilling the inclusion criterion.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `compositional_d5::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d5:043
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.72
- `assigned_category`: None
- `rationale`: The huge inner conjunction inside the NOT is false (acoramidis is not present, breaking one required subpart), so NOT(inner) is true, making the overall inclusion criterion satisfied via that NOT branch.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

### [HIGH] `compositional_d6::openai`

The model asserts the criterion predicate is present in the record while gold says not met. Either the generated record does state it (item is mislabelled), or it is underspecified and the item is unanswerable. Both are generator bugs being scored as reasoning failures.

- `item_id`: comp:d6:050
- `gold`: not_met
- `predicted`: met
- `confidence`: 0.62
- `assigned_category`: None
- `rationale`: The inclusion criterion is NOT of a large conjunction; evaluating the inner conjunction shows Part IV is false (pheochromocytoma absent and other branches false/undocumented), while several other parts are true (I: hypersensitivity present; II: systolic BP > 170 mmHg; III: drug-induced lichenoid lesion present; V: active tuberculosis present), making the inner conjunction false and thus NOT(inner) true, so the criterion is satisfied.

**Action.** Dump the full record for this item and adjudicate before attributing the error to the model.

## C6 — Depth-trend statistics

No findings.

## C7 — Missing leaderboard cells

No findings.

## C8 — Inference-parameter contradictions

No findings.

## C9 — Discrepancy list synchronisation

No findings.

## C10 — Polarity and structural coverage

No findings.

## Corrected selective-accuracy curves

Recomputed tie-aware where per-item confidences were recoverable; otherwise the run is listed as needing a rerun with per-item predictions persisted.

- `compositional_large::openai`: {'10%': 0.982759, '20%': 0.979885, '30%': 0.983333, '40%': 0.982008, '50%': 0.976818, '60%': 0.977315, '70%': 0.959801, '80%': 0.953958, '90%': 0.941319, '100%': 0.92}
- `compositional_d2::openai`: {'10%': 1.0, '20%': 1.0, '30%': 0.986111, '40%': 0.958333, '50%': 0.933333, '60%': 0.944444, '70%': 0.952381, '80%': 0.958333, '90%': 0.962963, '100%': 0.95}
- `compositional_d3::openai`: {'10%': 1.0, '20%': 1.0, '30%': 1.0, '40%': 1.0, '50%': 1.0, '60%': 1.0, '70%': 0.994709, '80%': 0.967593, '90%': 0.962963, '100%': 0.95}
- `compositional_d4::openai`: {'10%': 1.0, '20%': 1.0, '30%': 0.977778, '40%': 0.933333, '50%': 0.9, '60%': 0.902778, '70%': 0.904762, '80%': 0.875, '90%': 0.877315, '100%': 0.866667}
- `compositional_d5::openai`: {'10%': 1.0, '20%': 1.0, '30%': 0.916667, '40%': 0.819444, '50%': 0.788889, '60%': 0.805556, '70%': 0.809524, '80%': 0.786458, '90%': 0.759259, '100%': 0.716667}
- `compositional_d6::openai`: {'10%': 0.833333, '20%': 0.666667, '30%': 0.666667, '40%': 0.722222, '50%': 0.666667, '60%': 0.655556, '70%': 0.630952, '80%': 0.597222, '90%': 0.601852, '100%': 0.6}

## What this audit cannot see

- Per-item confidences and correctness are not stored in `paper_data.json`, only aggregates and the error subset. C1 is detected algebraically rather than recomputed. Persist per-item predictions so the corrected curve can be computed directly.
- Item text and patient records are absent, so C5 flags candidates but cannot adjudicate them.
- Nothing here validates the gold labels themselves.
