# Arm 1 verification: does the mapped form say what the criterion says?

**Status: first pass, AI-assisted. Not yet confirmed by the author.**
When the check below is done, replace this line with "Confirmed by the author on DATE".

## Why this exists

The Arm 1 gold label is the oracle's verdict on the *mapped form*, while the prompt shows
the model both the verbatim criterion and the form. Where the form does not say what the
sentence says, the gold label can be wrong for the sentence the model reads. Reviewers
asked that Arm 1 not be presented as performance on real criteria; the revision reports
it only where the label follows from the criterion as written.

`arm1_verification.csv` holds one row per Arm 1 criterion (463) with a `verdict`
(`keep` / `drop`) and a short `reason`. `scripts/rescore_real_criteria.py` reads it and
re-scores the released predictions. No model calls are needed.

## How to check it (about 1-2 hours)

1. Open `arm1_verification.csv` in Excel or Google Sheets.
2. Read `criterion_text` against `mapped_form`. Where you disagree with `verdict`, change
   it and edit `reason`. Leave rows you agree with alone.
3. Save as CSV (UTF-8) with the same columns, then run
   `python scripts/rescore_real_criteria.py`.
4. Update the status line above.

## The rule

**keep** — the form expresses every condition the sentence imposes, with the same
meaning, so the oracle's label is the label the sentence gives for the synthetic patient.
These differences are allowed:

- examples and definitions in parentheses (e.g. "(e.g., HIV)", "(Child-Pugh Class C)");
- words that add nothing testable ("known", "confirmed", "documented", "diagnosis of");
- the setting or the method of confirmation ("at screening", "by biopsy", "per MDRD");
- **a dropped disjunct** ("A or B" mapped to A). The synthetic record never documents B,
  so under three-valued evaluation the sentence's value is unknown, collapsed to not met,
  exactly when A is false: the label cannot change. These rows say so in `reason`.

**drop** — the form drops a condition the sentence requires, or changes its meaning:

- a dropped conjunct or requirement (surgery, pregnancy, sex, a second threshold);
- a dropped narrowing qualifier ("that cannot be safely interrupted", "newly diagnosed",
  "known to prolong the QTc interval");
- an inverted reading ("younger than 8 or older than 15" mapped to `age >= 8`;
  "not receiving dialysis" mapped to `dialysis`; "first-time use of X" mapped to `X`);
- a wrong entity, threshold or time window (creatinine for creatinine clearance; weeks
  of gestation read as years of age; "within 5 half-lives" read as any history);
- a fragment parsed as an entity ("by the treating ophthalmologist", "following agents").

A dropped disjunct *under a negation* would change the label; no kept row has one.

## The item-level rule (automatic; nothing to check)

Separately from the verdicts, the headline subset leaves out items in which a leaf with
no time qualifier has a fact that is present but recorded as not current. The oracle
counts such a leaf as met; the v2 prompt renders it as "present, not currently active";
and a present-tense criterion ("Receiving propofol for induction") does not settle which
reading is meant. `metrics.structure.currency_ambiguous_leaves` applies the rule.

## First-pass result (before the author's check)

337 criteria kept, 126 dropped. On the released predictions, accuracy is
0.965 [0.942, 0.980] on the 376 items in the headline subset, against 0.935 on all 926
items. Regenerate with `python scripts/rescore_real_criteria.py`.
