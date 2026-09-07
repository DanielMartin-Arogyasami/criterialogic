# Datasheet for CriteriaLogic

Following *Datasheets for Datasets* (Gebru et al., 2021). Covers the v0.2 release.

## Motivation

CriteriaLogic was created to measure whether a system resolves the **logical structure**
of clinical-trial eligibility criteria — nested AND/OR, negation and criterion-level
polarity, temporal windows, numeric thresholds — as opposed to recognising the right
entities or judging topical relevance. Its distinguishing property is that logical
nesting depth is an independent variable with programmatically-derived ground truth, so
a change in accuracy across depth is attributable to structure and not to vocabulary,
topic, or prompt design.

Created by the author as independent research. No funding. No institutional data access.

## Composition

Two arms, both derived from one dated ClinicalTrials.gov API v2 snapshot. There is no
licence-restricted component.

- **Arm 1 — real criteria.** Criteria segmented verbatim from the snapshot's
  `eligibilityCriteria` text and mapped onto the logical form, carrying the polarity of
  the section they came from. Precision over recall: a sentence that cannot be mapped
  faithfully is skipped and counted, never coerced. Exact counts, mapping rate, polarity
  split and depth histogram: `python scripts/build_real_criteria.py --stats`.
- **Arm 2 — compositional stress test.** Nested AND/OR/NOT expressions at controlled
  depths, composed from atoms extracted from the same snapshot, paired with seeded
  synthetic patient records. The atoms are real trial predicates carrying their source
  NCT IDs; **the nesting and the patients are synthetic by construction**, and every item
  records `metadata["composition"] = "synthetic"`.

The committed snapshot: 300 studies, frame recorded field by field in
`data/ctgov_cache/MANIFEST.json`, fetched 2026-08-29, atoms from trials first posted
between 2026-06-30 and 2026-08-28. Extraction matched 675 of 4,869 candidate sentences
(13.9%), yielding 522 distinct atoms from 222 trials.

**Patients are synthetic in both arms.** That is the honest limit of the release: it
measures reasoning over a stated record, not evidence-finding in a real clinical note.

## Collection

ClinicalTrials.gov records are US Government public domain, retrieved from the public v2
REST API at no more than two requests per second. No human subjects are recruited and no
new patient data is collected. Synthetic patient facts are generated deterministically
from a seed, sampled near constraint boundaries so that both sides of each threshold
occur.

## Preprocessing / harmonisation

Everything maps onto one logical form (`criterialogic/schema/logical_form.py`): atoms
with optional temporal and numeric constraints, n-ary AND/OR groups, unary NOT, and a
criterion-level polarity label kept **separate** from logical negation. Corpus-level
checks (unique ids, schema-version consistency, trial-keyed split leakage) run over
collections. Extraction and segmentation yields are recorded in the artifacts, not just
the items that succeeded.

## Uses

A research benchmark for eligibility-logic reasoning and for error analysis.
**Not a medical device.** It makes no patient-care claims and is intended for offline
evaluation. Do not deploy a system on the basis of an aggregate score from it: the whole
design premise is that aggregates hide construction-specific failures.

Known unsuitable uses: estimating real-world screening performance (synthetic patients);
claiming coverage of complex criteria (extraction is conservative by design); treating
depth-5 or depth-6 accuracy as a frequency-weighted estimate of anything (real criteria
are overwhelmingly shallow — see the depth histogram).

## Distribution

MIT licence, on GitHub, with the snapshot and atom pool committed. The snapshot is
deposited with the release under its own identifier so a specific version of the data can
be cited independently of the code.

## Maintenance

Versioned via `SCHEMA_VERSION`, the package version, the atom pool SHA-256, the
prompt-renderer version and the failure-labeller version — all recorded into every result
file. Issues and PRs on GitHub. Known gaps and their status are tracked in
`results/DISCREPANCIES.md`; deferred components in `docs/V2_SCOPE.md`.
