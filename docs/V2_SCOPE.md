# Deferred to v2

v0.2 cut scope deliberately, to ship a preprint with real numbers rather than a larger
design with placeholders. This file records what was removed, why, and what it would take
to restore — so a reader can see the deferral as a decision rather than an omission. The
removed code is in the git history at the v0.1 tag.

## Cut: the Chia structuring task

v0.1 defined a task that parsed free-text eligibility into the logical form, scored
against the Chia corpus (Kury et al. 2020) with entity F1, relation F1, and canonicalised
logical-form exact match.

**Why cut.** Converting Chia's brat-standoff annotations onto the schema is a month of
work on its own: the released loader handled the common patterns but the DAG-to-tree
reduction for deeply nested criteria and the `Has_value`/`Has_temporal` attachment onto
atom constraints were both incomplete. A structuring task scored against a partial
mapping measures the mapping.

**To restore.** Finish `doc_to_logical_forms`, then reinstate `metrics/extraction.py`
(entity/relation F1 and exact match, which the schema's `canonicalize` already supports).
Nothing in the current schema blocks it.

## Cut: the n2c2 2018 cohort-selection matching task

v0.1 encoded the 13 public n2c2 criterion definitions as logical forms and evaluated
met/not-met against them.

**Why cut.** The patient records are gated behind a data-use agreement that may require
an institutional signature the author cannot provide, and it was the project's only
external dependency with an unbounded lead time. Worse, the released component never
used the real records at all: it paired the real criterion definitions with synthetic
patients, and the audit found that four of the five reported model errors were on items
whose gold label rested on a fact the prompt did not state. All 13 criteria were
`polarity=inclusion`, so criterion-level polarity — the thing the schema keeps separate
from logical negation, and the first category in the failure taxonomy — was never
exercised.

**What replaced it.** Arm 1 (`criterialogic/data/real_criteria.py`) segments criteria
from the ClinicalTrials.gov snapshot. Those carry real exclusion polarity, which the
n2c2 component never did.

**To restore.** Obtain the DUA, place the records under `data/raw/n2c2_2018/`, and write
a loader mapping records onto `PatientFacts`. Matching against real longitudinal records
is the single most valuable v2 addition, because both current arms use synthetic patients.

## Cut: the criterion typing and polarity task

Most of it was derivable from the structuring task, and polarity already appears in the
failure taxonomy as category 1. It went with Chia.

## Cut: encoder fine-tuning baselines

BioClinicalBERT, PubMedBERT, BioBERT. `models/encoder.py` raised `NotImplementedError`
and needed `transformers`, `torch`, and a fine-tuned checkpoint per task. A stub that
raises is a promise, not a baseline, and it read as a shipped component in the module
list. Restoring it means a training loop, which is a different project shape from an
inference-only harness.

## Cut: open-weight LLM baselines

`models/llm_local.py` was also a stub. Restoring it needs an HF or vLLM runtime; the
`Model` interface it would implement is unchanged and three lines wide.

## Cut: the hosted leaderboard

No Hugging Face Space, no site, no automatic scoring on submission, no UI. What remains
is the part that matters: one `Model` interface, a submission format, a validator, a
scorer, and a table in the README that is updated by hand. A leaderboard with two
entries does not need hosting.

## Cut: the second atom pool

v0.1 could compose the stress test over either ClinicalTrials.gov atoms or the leaf
predicates of the n2c2 criteria. The second supported no contamination argument — those
criteria predate every evaluated model — and a second pool invites silent mixing.

## Cut: intra-annotator test-retest reliability

That was the fallback for having only one annotator. v0.2 has two, so the reported
reliability is inter-annotator agreement with a bootstrap interval.

## Cut: the schema's cardinality node

"Two or more of the following four" is still expanded to disjunctive normal form rather
than represented natively. Exact but verbose. A native `Cardinality` node remains a v2
item; nothing currently in the benchmark exercises it.
