# CriteriaLogic annotation codebook

**Version 1.0** · for the reasoning-failure taxonomy in the CriteriaLogic benchmark

This codebook is the instrument. Two annotators label the same error sample
independently and blind to each other, using only this document. Whatever agreement
that produces is what gets reported — including a low figure, which would be a real
finding about how hard error attribution is rather than something to fix by relabelling.

Revision history is at the end. Revisions made during the calibration session are
recorded there; items labelled during calibration are discarded and do not enter the
statistics.

---

## 1. What you are labelling

Each row is one **error**: a case where a model's met/not-met decision disagreed with
the gold label. You are answering one question:

> **Which single feature of the criterion did the model most plausibly get wrong?**

You are *not* judging whether the model's answer was reasonable, whether the criterion
was well written, or whether the gold label is correct. If you think the gold label is
wrong, that is what the `notes` column is for — say so and still assign your best
category, because the adjudication step needs your reading either way.

### Columns you fill

| Column | What goes in it |
|---|---|
| `category` | Exactly one of the seven category names in §3, lowercase, spelled as written there. |
| `clinical_judgement_required` | `yes` if your category decision depended on medical knowledge — knowing what a drug is for, which conditions are related, what a lab value means clinically. `no` if you decided it from the logical and linguistic structure alone. |
| `notes` | Anything the adjudicator needs: doubts, a second candidate category, a suspected gold-label error. Optional but valuable. |

The `clinical_judgement_required` flag is not a confidence rating. A decision can be
completely confident and still depend on clinical knowledge, and it can be uncertain
for purely linguistic reasons. Tick it based on *what kind* of knowledge you used, not
how sure you were.

### Columns you read

`criterion` is the criterion as the model saw it, including its logical form and its
polarity (inclusion or exclusion). `patient_facts` is the record as the model saw it.
`gold` and `predicted` are the two decisions. `model_rationale` is the one-sentence
explanation the model gave, when it gave one.

Read the rationale, but do not defer to it. A model can reach the right answer with bad
reasoning or the wrong answer with a rationale that misdescribes what it did. Where the
rationale and the structure of the error point at different categories, the structure
governs — unless the rationale contains a constraint that is not in the criterion at
all, which is category 7.

---

## 2. Decision order

Work down this list and stop at the first category that fits. The order exists because
several categories can technically apply to one error, and without a fixed order the two
annotators are answering different questions.

1. **Fabrication** (§3.7) — does the rationale assert a constraint that is not in the
   criterion? Check this first: an invented constraint explains the error completely, and
   the error will usually *also* look like a composition or threshold problem.
2. **Negation / polarity** (§3.1) — is a NOT dropped, mis-scoped, or is an exclusion
   being treated as an inclusion?
3. **Numeric threshold** (§3.3) — is a comparator or boundary handled wrongly?
4. **Temporal** (§3.2) — is a window, tense, or currency handled wrongly?
5. **Entity conflation** (§3.5) — has the model matched the wrong clinical concept?
6. **Implicit knowledge** (§3.6) — did the criterion require an unstated inference?
7. **Logical composition** (§3.4) — is the AND/OR structure resolved wrongly?

Note that logical composition is **last**, not first. It is the residual category for
compound criteria: almost every error on a nested criterion can be described as "the
composition came out wrong", so treating it as the first match would absorb everything
and the taxonomy would carry no information. Only assign it when the error is in the
*combination* of correctly-read parts.

If nothing fits, use `none` and explain in `notes`. Do not stretch a category to avoid
an unattributed label; the count of unattributed errors is itself a reportable number.

---

## 3. The seven categories

### 3.1 `negation_polarity`

**Definition.** The model dropped a logical NOT, applied it to the wrong scope, or
treated an exclusion criterion as though it were an inclusion criterion (or vice versa).

**Positive examples.**

- Criterion: `NOT (history of stroke)`. Patient: stroke present. Gold: not met. Model:
  met, rationale "the patient has a history of stroke, satisfying the criterion." The NOT
  was dropped.
- Criterion: `NOT (A AND B)`, patient satisfies A but not B. Gold: met (the conjunction
  is false, so its negation is true). Model: not met, rationale "B is not satisfied so
  the criterion fails." The negation was applied to A and B individually rather than to
  the conjunction — mis-scoped, still this category.

**Negative examples — what this is commonly confused with.**

- Criterion: `NOT (A OR B)` where the model correctly negates but then evaluates
  `A OR B` wrongly because it read the OR as an AND. The negation was handled; the
  combination was not. That is **`logical_composition`** (§3.4).
- An **exclusion** criterion where the model correctly understands that a match means
  the patient is excluded, but gets the underlying predicate wrong for a threshold
  reason. The polarity was handled; assign the threshold category.

**Clinical judgement:** almost never. Tick `no` unless something unusual is going on.

---

### 3.2 `temporal`

**Definition.** The model mishandled a time qualifier: a lookback window ("within six
months"), a duration ("for at least three months"), currency ("current", "ongoing",
"active"), or unbounded history ("ever", "any history of").

**Positive examples.**

- Criterion: `myocardial infarction (within the past 6 months)`. Patient: MI most recent
  occurrence ~400 days ago. Gold: not met. Model: met, rationale "the patient has a
  history of myocardial infarction." The window was ignored.
- Criterion: `aspirin (current / ongoing)`. Patient: aspirin present, not currently
  active. Gold: not met. Model: met, rationale "aspirin is present, indicating ongoing
  use." Currency was read off presence.

**Negative examples.**

- The patient facts do not state the timing at all and the criterion needs it. The
  model had nothing to reason from. Check whether the row is flagged unanswerable; if
  the fact's currency or recency is simply absent from the prompt, use `none` and say so
  in `notes` — this is a defect in the item, not a model failure. (The export normally
  excludes these, but say so if one slips through.)
- Criterion mentions "history of X" and the model gets X itself wrong. That is
  **`entity_conflation`** (§3.5); the temporal qualifier was not the problem.

**Clinical judgement:** rarely. Occasionally yes, where knowing whether a condition is
chronic or acute is what makes a duration reading right or wrong.

---

### 3.3 `numeric_threshold`

**Definition.** The model mishandled a numeric bound: the wrong comparator (`>` read as
`>=`), an inverted bound, a boundary value decided wrongly, one side of a range missed,
or a unit ignored.

**Positive examples.**

- Criterion: `HbA1c between 6.5 and 9.5 %`. Patient: HbA1c 9.8. Gold: not met. Model:
  met, rationale "HbA1c is elevated, consistent with the criterion." The upper bound was
  not applied.
- Criterion: `eGFR < 45`. Patient: eGFR 45.0. Gold: not met (strict inequality). Model:
  met. A boundary error — this category even though the miss is by nothing.

**Negative examples.**

- The value is absent from the patient facts and the model guessed. If the criterion's
  convention for an undocumented value was stated in the prompt and the model ignored
  it, that is closer to **`none`** or `logical_composition` depending on the structure;
  note your reasoning.
- A range that the model reads correctly but then combines wrongly with another
  condition: **`logical_composition`**.

**Clinical judgement:** usually `no` — comparators and boundaries are arithmetic.
Tick `yes` if you needed to know a reference range or a unit convention to decide.

---

### 3.4 `logical_composition`

**Definition.** The model read the individual parts correctly but combined them wrongly:
AND treated as OR, OR treated as AND, a nested group's scope misread, or a disjunction
satisfied by one branch reported as unsatisfied.

**Positive examples.**

- Criterion: `(A OR B) AND C`. Patient satisfies B and C. Gold: met. Model: not met,
  rationale "A is not satisfied." The OR was treated as requiring both branches.
- Criterion: `A AND (B OR C)` at depth 2. Patient satisfies A and C. Gold: met. Model:
  not met, rationale that tracks A and B and never reaches C.

**Negative examples — read these carefully, this category is over-assigned.**

- Any error on a nested criterion is *not* automatically composition. Check the earlier
  categories first: if ignoring the criterion's one temporal window would have produced
  the model's answer, it is **`temporal`**, even though the criterion is nested.
- `NOT (A AND B)` handled as `NOT A AND NOT B` is a **negation scope** error (§3.1), not
  composition, because the mistake is in what the NOT applies to.

**Clinical judgement:** essentially never. Tick `no`.

---

### 3.5 `entity_conflation`

**Definition.** The model treated two clinically distinct concepts as the same one, or
matched a criterion's concept against a different concept in the record.

**Positive examples.**

- Criterion: `type 2 diabetes mellitus`. Patient: type 1 diabetes present. Model: met.
- Criterion: `metformin`. Patient: on a different antidiabetic. Model: met, rationale
  "the patient is on diabetes medication."

**Negative examples.**

- The record uses a synonym for the same concept and the model matched it correctly.
  That is not conflation, and not an error at all if the answer was right.
- A criterion naming a drug class where the patient is on a member of that class. Whether
  that is conflation or a correct reading is exactly a clinical judgement — tick the flag
  and use `notes`.

**Clinical judgement:** almost always `yes`. This is one of the two categories that
needs medical knowledge, and where the two annotators are expected to diverge. The
adjudication rule for it is in §4.

---

### 3.6 `implicit_knowledge`

**Definition.** The criterion required an inference the text does not state, and the
model failed to make it. "Adequate organ function", "clinically significant", "able to
comply with the protocol" — phrases whose meaning is a set of specific facts the
criterion does not enumerate.

**Positive examples.**

- Criterion: `adequate renal function`. Patient: creatinine value given, no explicit
  "adequate renal function" fact. Model: not met, rationale "adequate renal function is
  not documented." The inference from the creatinine value was required and not made.
- Criterion: `no clinically significant cardiac disease`. Patient: a minor, non-significant
  finding present. Model: not met, treating any cardiac finding as significant.

**Negative examples.**

- The criterion states its own threshold explicitly. Then no inference was required, and
  a wrong answer is a threshold error.
- The model invented a specific threshold for a vague phrase and applied it. That is
  **`fabrication`** (§3.7) — it asserted a constraint the criterion does not contain.
  The line between the two is: failing to infer is §3.6, inventing a specific bound is
  §3.7.

**Clinical judgement:** almost always `yes`. The second of the two clinical categories.

---

### 3.7 `fabrication`

**Definition.** The model's reasoning asserts a constraint that is not present in the
criterion at all.

**Positive examples.**

- Criterion: `age >= 18 years`. Model: not met, rationale "the patient is 82, above the
  upper age limit of 75." There is no upper limit in the criterion.
- Criterion: `metformin (current)`. Model: not met, rationale "the criterion requires at
  least three months of metformin therapy." No duration is stated.

**Negative examples.**

- A rationale that misstates the *value* of a real constraint (says "> 7.5" for a
  criterion that says "> 7.0") is a **`numeric_threshold`** error: the constraint exists,
  the model got it wrong.
- A rationale that is merely vague or unhelpful but does not assert anything false is
  not fabrication. Judge the category from the structure instead.

**Clinical judgement:** usually `no`. Checking whether a constraint appears in the
criterion is a reading task.

---

## 4. Adjudication

Every disagreement is adjudicated and the resolution recorded. Two rules:

- **Where the disagreement is clinical** — either annotator ticked
  `clinical_judgement_required` — **annotator 1 governs.** Annotator 1 is a clinical data
  professional with trial-eligibility experience; annotator 2 was selected for linguistic
  and logical precision. The paper states this rule and states that entity conflation and
  implicit-knowledge gap therefore remain effectively single-annotator categories.
- **Where the disagreement is linguistic or logical**, resolve it on the merits by
  rereading this codebook together. Neither annotator wins by default. If the
  disagreement traces to wording in this document, revise the wording and record it in
  §6 — but do **not** relabel already-completed items, because relabelling after seeing
  the agreement figure is how a reliability estimate stops meaning anything.

---

## 5. The automatic labeller

A heuristic labeller in the toolkit assigns a candidate category by counterfactual
probing of the structured form. **Neither annotator sees its output while labelling.**
Its agreement with the human consensus is reported separately as a third signal.

It is a triage aid, not a gold standard, and it structurally cannot assign
`entity_conflation`, `implicit_knowledge` or `fabrication` — those concern the
relationship between the criterion and the world, which no counterfactual over the
logical form can reach. Where the consensus label is one of those three, agreement with
the labeller is impossible by construction, and the report counts those items so the
figure can be read correctly.

---

## 6. Revision history

| Version | Date | Change | Reason |
|---|---|---|---|
| 1.0 | — | Initial version. | Written before any annotation, per the project plan. |
| | | *(calibration-session revisions recorded here)* | |

Record every revision with the disagreement that prompted it. The twenty items labelled
in the calibration session are discarded and excluded from all reported statistics.
