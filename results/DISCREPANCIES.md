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

- **Status:** open
- **Location:** manuscript §3.4 vs `criterialogic/tasks/compositional.py::_atom_pool`
- **Paper says:** Task D atoms are extracted from real ClinicalTrials.gov criteria.
- **Code does:** the atom pool is built from the leaf predicates of the 13 public n2c2 criterion
  definitions. No ClinicalTrials.gov text is fetched anywhere in the generation path. The source
  enum value `CTGOV_SYNTHETIC` compounds the problem by implying provenance the data does not
  have.
- **Consequence:** the paper describes a data source the code never touches, and §3.5's
  contamination argument has no evidence behind it, since n2c2 criterion text long predates the
  training cutoff of every evaluated model.
- **Action:** either implement a genuinely ClinicalTrials.gov-derived pool (work item W1) or
  change the wording to "atoms drawn from the public n2c2 criterion definitions." Resolving it in
  code is preferred, because the contamination claim depends on recency of the source trials.
- **Detected by:** `collect_paper_data.py`, which emits this entry into `paper_data.json`.

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
