# Discrepancies between the manuscript draft and the implementation

Register of places where the paper and the code disagree, or where the code cannot support a
claim the paper makes. Per the standing repository rules, code changes never rewrite a
scientific claim: a discrepancy is recorded here and the author decides the wording.

**Status vocabulary.** `open` — unresolved. `resolved-in-code` — the implementation now matches
the paper; the manuscript may still need a wording check. `resolved-in-paper` — the author
changed the wording; no code change required. `wontfix` — deliberate, with the reason stated.

Every entry must name the file and symbol involved, so the claim can be re-checked after a
refactor. Do not enter a numeric value here that was not produced by executing code.

---

## 1. Task D atoms are not drawn from ClinicalTrials.gov

- **Status:** resolved-in-code — **§3.4 needs a wording check by the author**
- **Location:** manuscript §3.4 vs `criterialogic/tasks/compositional.py::_atom_pool`
- **Paper said:** Task D atoms are extracted from real ClinicalTrials.gov criteria.
- **Code did:** the atom pool was built from the leaf predicates of the 13 public n2c2 criterion
  definitions. No ClinicalTrials.gov text was fetched anywhere in the generation path, and the
  source enum value `CTGOV_SYNTHETIC` implied provenance the data did not have.
- **Resolution (work item W1).** `criterialogic/data/loaders/ctgov.py` now fetches Phase-IV
  interventional studies from the public v2 API into `data/ctgov_cache/` and extracts atoms from
  the verbatim eligibility text. `data/ctgov_atom_pool.json` is the pool the generator reads;
  each atom records its source NCT ID, the source sentence, that trial's first-posted date, and
  the extraction rule that fired. `_atom_pool()` raises `AtomPoolUnavailable` when the file is
  absent rather than falling back. `Source.CTGOV_SYNTHETIC` is gone, replaced by `Source.CTGOV`,
  `Source.N2C2_DERIVED`, and `Source.SYNTHETIC_EXAMPLE`, and every generated item records which
  pool it used.

**What the author still has to decide.** §3.4 can now claim ClinicalTrials.gov provenance, but
only with these qualifications, which the code enforces and the wording should match:

1. **The atoms are real; the nesting is not.** Composition into depth-1..4 AND/OR/NOT trees is
   synthetic by construction, and the patients evaluated against them are synthetic. Every item
   carries `metadata["composition"] = "synthetic"` for exactly this reason. §3.4 should not
   imply that real trials state criteria at these nesting depths.
2. **Extraction is a conservative rule-based pass, not a parser.** It matched 675 of 4,869
   candidate sentences (13.9%) across 300 trials, yielding 522 distinct atoms from 222 trials.
   Coordinated phrases, comma enumerations, and bounds stated relative to a reference range are
   skipped rather than coerced, so the pool under-represents complex criteria by design. If §3.4
   describes coverage, that ratio is the honest number and it is recorded in the pool file under
   `extraction`.
3. **Predicates are extracted without the source criterion's polarity.** An atom taken from
   "No history of Parkinson's disease" is the predicate *history of Parkinson's disease*; the
   exclusion sense is not carried into the atom, because Task D applies its own negation.
4. **The contamination claim is now supported, and dated.** Every atom in the committed pool
   comes from a trial first posted between 2026-06-30 and 2026-08-28. §3.5 can cite that range,
   but it is a property of this pool file, not of the method — a rebuild with a different
   `--first-posted-from` changes it, and the pool's SHA-256 is recorded on every generated item.

## 2. Monotonic decline with nesting depth is not established

- **Status:** open
- **Location:** manuscript §7.2 hypothesis vs the measured depth curves
- **Paper says:** accuracy declines monotonically with logical nesting depth.
- **Data shows:** the per-depth accuracies in the §7.2 table of `results/paper_data.md` are not
  monotonic for every system at the sample sizes run. The 36-item demo set carries only 12 items
  per depth, which cannot resolve a trend of the size hypothesized, and no confidence interval or
  rank-correlation test has been computed.
- **Action:** state the observed pattern rather than asserting monotonicity, and attach the
  statistics from work item W11 (Spearman correlation with a p-value, Wilson intervals on each
  per-depth accuracy, and the n-per-depth required for 80% power). If the required n exceeds what
  was run, §7.2 should state the limitation with that number attached.
- **Detected by:** `collect_paper_data.py`, which emits this entry into `paper_data.json`.

## 3. Requested inference parameters were not the effective ones

- **Status:** open
- **Location:** manuscript §6 and §9 vs `criterialogic/models/llm_api.py`
- **Paper says:** inference parameters are reported for every evaluated system.
- **Code does:** the adapter requests `temperature=0.0`; `gpt-5-nano` rejects a custom
  temperature, so the adapter retries without it and the API default applies. The dropped
  parameter is not recorded in the cache entry, so a run cannot be reconstructed from the cache
  alone, and the cache key does not include the effective parameters.
- **Consequence:** the determinism the paper implies for the one real model in the study is not
  demonstrable from the artifact.
- **Action:** work item W6 — record requested versus effective parameters per call inside the
  cache entry, and key the cache on the effective parameters so a parameter change invalidates it.
