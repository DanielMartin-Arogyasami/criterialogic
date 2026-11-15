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

## 4. Task C items whose gold label rests on a fact the prompt never states

- **Status:** open — **blocks the §7.3 failure taxonomy**
- **Location:** `criterialogic/models/llm_api.py::render_patient` vs
  `criterialogic/oracle.py::_check_temporal`
- **Paper says:** §7.3 attributes the `gpt-5-nano` matching errors to reasoning failures, four of
  them to the temporal category.
- **Code does:** `Fact.current` is a plain `bool` defaulting to `False`, and `_check_temporal`
  returns it directly for `TemporalOp.CURRENT`, so `current=False` is a definite *false* rather
  than *unknown*. `render_patient` emits `"currently active"` only when `current` is true and
  emits nothing when it is false. A present-but-not-current fact therefore renders as
  `- aspirin for mi prophylaxis: present`, which is textually identical to a fact whose currency
  was never recorded.
- **Consequence:** for `match:ASP-FOR-MI:{000,001,003,006}` and `match:ALCOHOL-ABUSE:000` the gold
  label is `not_met` on the strength of a field the prompt does not contain. The model answered
  `met` and gave one verbatim rationale across the four aspirin items — the reading the prompt
  actually supports. These are unanswerable items (verdict **B** in
  `results/missing/SUSPECT_ITEMS.md`), not temporal-reasoning failures, and they are 4 of the 5
  errors the taxonomy is computed from.
- **Evidence:** `results/missing/suspect_items.json`, dumped by `python run_missing.py
  --dump-suspects`; the oracle's own verdict is correct given the record, so this is a rendering
  defect, not an oracle defect.
- **Action:** two candidate fixes, both changing Task C numbers, so the author picks before any
  rerun. (a) Make the renderer total over the fields the oracle reads — emit
  `"not currently active"` when `current` is false — which makes the items answerable and keeps
  the labels. (b) Make `Fact.current` tri-state (`bool | None`) so *unknown currency* is
  representable and the oracle returns `None` for it, which is the more faithful model but
  changes gold labels and the unknown-collapse convention. Until one is applied, §7.3 must not
  report these four items as temporal reasoning failures.

---

# v0.2 entries

## 5. The scope cuts, and what they removed from the manuscript's claims

- **Status:** resolved-in-code — **manuscript rewritten to match**
- **Location:** manuscript §§1-3, 6, 9, 11 vs the package contents
- **What changed.** The Chia structuring task, the criterion typing/polarity task, the
  n2c2 2018 matching task, the encoder baselines, the open-weight LLM stub, the second
  atom pool, the hosted leaderboard and the intra-annotator test-retest pass are all
  gone. See docs/V2_SCOPE.md for each one's reason and restoration path.
- **Consequence for the claims.** The benchmark is no longer "harmonized across
  gold-standard resources" — there is one source. The task count changed again, and the
  abstract, §1 contributions, the §3.3 table and §11 were updated in one pass to say two
  arms plus one cross-cutting layer. The DUA pointer is removed from §9 because there is
  no gated component.

## 6. "First public benchmark" does not survive a prior-art check

- **Status:** resolved-in-paper
- **Location:** manuscript abstract, §1, §11
- **What the draft said.** "To our knowledge the first standardized public benchmark
  that isolates logical-reasoning failures in clinical-trial eligibility matching."
- **What the literature shows.** NLI4CT (Jullien et al., SemEval-2023 Task 7 / EMNLP
  2023) is already a public benchmark requiring logical and numerical reasoning over
  clinical trial text. Criteria2Query 3.0 (Park et al., JBI 2024) already publishes an
  error taxonomy over GPT-4 eligibility-query generation in which logic errors are the
  most common category. Multiple 2024-2026 works analyse negation and exclusion-criteria
  failures specifically. The TREC Clinical Trials tracks 2021-2023 are the standing
  retrieval benchmark.
- **Resolution.** The novelty claim is repositioned onto what the prior art does not do:
  logical nesting depth as a *controlled independent variable* with programmatically
  derived ground truth, reported jointly with error attribution and calibration. Stated
  with "to our knowledge" and with the prior art cited in §2 rather than omitted.

## 7. The reported depth curve is confounded by the prompt renderer

- **Status:** open — **disclosed in §7, fix shipped as renderer v2, re-run required**
- **Location:** `criterialogic/models/llm_api.py::render_patient` vs
  `criterialogic/oracle.py::_check_temporal`
- **Problem.** Entry 4 above identified this for the matching task. It applies to the
  compositional arm too, and worse: exposure rises with depth because deeper items
  contain more atoms. 4 of 60 items at depth 2, 55 of 60 at depth 6.
- **What bounds it.** Error rates are near-identical across exposed and unexposed strata
  at the depths carrying the finding (0.400 vs 0.400 at depth 6), and the decline
  survives conditioning on unexposed items across depths 2-5 (rho = -1.000, exact
  p = 0.0417). Depth 6 is uninformative after conditioning (n = 5).
- **Resolution.** `PROMPT_VERSION = "2"` makes the rendering total and is now the
  default; v1 is retained so the reported numbers stay regenerable from the shipped code
  (`--prompt-version 1`). The prompt version is part of the cache key, so the two cannot
  be mixed in one result file. **§7 reports both the unconditioned and conditioned
  curves.** A v0.3 re-run under renderer v2 is the first outstanding item.

## 8. The v1 failure-taxonomy distribution described the labeller, not the model

- **Status:** resolved-in-code — **§7 reports the v2 distribution**
- **Location:** `criterialogic/taxonomy/annotate.py::categorize_error`
- **Problem.** v1 tested `depth >= 1` before the temporal and numeric probes. Every item
  in the compositional arm is nested by construction, so that branch absorbed all of
  them and only two of seven categories were ever reachable. The reported
  `logical_composition 59, negation_polarity 28` was therefore a property of the decision
  order.
- **Resolution.** v2 runs the constraint-type probes before the depth catch-all, adds an
  unanswerable gate (entry 7), and stops guessing IMPLICIT_KNOWLEDGE for unexplained flat
  errors — that category needs knowledge of what the model had to infer, which no
  counterfactual over the form can establish. `LABELLER_VERSION` is recorded in every
  result file. Recomputed pooled distribution: logical_composition 50,
  negation_polarity 28, temporal 6, numeric_threshold 3.
- **Also fixed.** `reachable_categories()` states in code that entity conflation,
  implicit knowledge and fabrication are human-only, so a report can say why three rows
  are empty rather than leaving a reader to infer it.

## 9. The committed snapshot has no recruitment-status filter

- **Status:** open, by decision — **§3 describes the frame as it is**
- **Location:** `data/ctgov_cache/MANIFEST.json` vs the project plan
- **Plan said.** Restrict the snapshot to recruiting studies.
- **Reality.** The committed snapshot's frame is Phase-4 interventional, first posted
  ≥ 2026-01-01, with no `AREA[OverallStatus]` clause. `StudyQuery.overall_status` and
  `scripts/fetch_ctgov_snapshot.py --recruiting` now exist, and the frame is recorded
  field by field in the manifest.
- **Why not applied.** A rebuild changes the atom pool digest, which changes every
  generated item, which invalidates every number in results/SECTION7.md and requires new
  API calls to restore. The reported depth finding exists now; the recruiting filter
  would improve the frame's fit to the deployment story without changing what the arm
  measures.
- **Action.** §3 states the frame verbatim from the manifest and does not claim a
  recruiting restriction. Apply it at the next rebuild, when the results are being
  regenerated anyway.

## 10. One model is not a baseline ladder

- **Status:** open — **manuscript §6 scoped to match**
- **Location:** manuscript §6 vs `criterialogic/models/REGISTRY`
- **Problem.** The plan called for four or five systems: two open-weight, one or two
  commercial, one reasoning model. The available API project grants `gpt-5-nano` only;
  other models return `403 model_not_found`. The two offline entries are diagnostics, not
  systems — one is the oracle, the other is deliberately broken.
- **Action.** §6 describes one evaluated system and says so plainly; §7 and the
  Discussion state that the depth result is a measurement of that system and that
  generalisation across model classes is untested. This is a claim boundary, not a gap
  to be papered over with the two offline rows.

## 11. Arm 1 expressions are partial readings of their source sentences

- **Status:** resolved-in-code and **resolved-in-paper** (§3.2 reframed)
- **Location:** `criterialogic/data/real_criteria.py::sentence_to_expression` vs manuscript §3.2
- **Problem.** The extractors were built to mine *predicates* for the atom pool, where
  partiality is harmless because the stress test supplies its own structure. Reused to build
  criterion-level forms, the partiality is inherited: "Patients aged 19 to 79 years
  undergoing elective non-cardiac surgery expected to last 60 minutes or longer" maps to
  `age between 19 and 79` and drops the surgical requirement. The draft's §3.2 read as though
  the form were a translation of the sentence.
- **Worse subclass, now fixed.** For an un-comma'd conjunction whose coordination mapping
  failed, the single-atom fallback dropped a conjunct. "Participants must have BMI >= 18 and
  <= 40" yielded `bmi >= 18`, a criterion that admits a patient with BMI 45 whom the trial
  excludes. Dropping a conjunct weakens the criterion and flips gold labels toward "met",
  producing exactly the mislabel class the project says is worse than lower yield.
  `_has_unmapped_conjunction` now rejects those sentences; a sentence mixing "and" with "or"
  is rejected outright.
- **Resolution.** Every form records `metadata["coverage"] = "partial_predicate"`. §3.2 now
  describes Arm 1 as testing decisions over a real predicate drawn from real criterion text
  with the real polarity of its section, explicitly *not* as testing whole-criterion
  semantics, and states that nearly all Arm 1 forms are depth 0.
- **Consequence for the two-arm design.** Arm 1 can corroborate the shallow end of the depth
  curve and nothing deeper. §7.6 and Limitations say so. A real realism check on compound
  criteria requires the deferred structuring task (docs/V2_SCOPE.md).

## 12. Five smaller defects found in review

All resolved in code; none changes a reported number.

| # | Location | Defect | Fix |
|---|---|---|---|
| a | `real_criteria._coordinated_expression` | A sentence with both "and" and "or" was resolved to OR over all parts, assigning one of two possible readings. | Reject mixed coordination. |
| b | `eval/runner.run_task` | `per_item_predictions` omitted the model's rationale, so the annotation export shipped an empty `model_rationale` column — the column docs/CODEBOOK.md tells annotators to read, and the only evidence for category 7 (fabrication). | Rationale persisted per item. |
| c | `taxonomy/reliability._error_rows` | Rendered patient records with prompt renderer v2 while the evaluated run used v1, so annotators would have judged a prompt the model never saw — and the two renderings differ on exactly the items most at risk of misattribution. | `prompt_version` threaded through `sample_error_set`, `export_for_annotation` and `scripts/annotation_export.py --prompt-version`. |
| d | `metrics/logic.accuracy_by_depth` | An item with `depth is None` was folded in under a `-1` sentinel, which could enter the trend statistics as a real depth level. | Undepthed items contribute to the overall figure only; `n_items_without_depth` is reported. |
| e | `data/real_criteria.py` | Unused `Atom` import — ruff F401, which would have failed CI. | Removed. |

## 13. Security and robustness audit — nine defects

Found in a dedicated adversarial review; all fixed, with `tests/test_security.py` (21
tests) covering every case. None changes a reported number.

**Threat model.** The toolkit fetches third-party JSON over the network and turns fields
of it into filenames and LLM prompt text; it writes CSVs that two human annotators open in
a spreadsheet; and it ingests leaderboard submissions from strangers.

| # | Severity | Location | Defect |
|---|---|---|---|
| a | **High** | `models/llm_api.py` | **Exclusion-polarity prompt ambiguity.** The prompt showed `(exclusion criterion) X` and asked "Does the patient satisfy the criterion?" while gold is the truth of `X`. Two readings, opposite labels. Harmless for the reported results (the compositional arm is entirely inclusion-polarity) but it would have produced a large spurious error rate on the real-criteria arm, which draws mostly from exclusion sections, and filled the negation/polarity category with prompt artefacts rather than model failures. Fixed in prompt v2, which asks whether the condition holds and states the exclusion rule explicitly; v1 is frozen for prompt reproducibility. |
| b | **High** | `data/loaders/ctgov.py` | **Path traversal.** `nctId` arrives in a remote response body and was used unvalidated as a filename by `cache_path`, and as a URL path segment by `fetch_eligibility` (where `quote` does not escape `/` by default). A response carrying `../../../etc/cron.d/x` would write outside the cache. Fixed with an anchored `^NCT\d{8}$` check at every boundary; `_write_cache` skips a bad record rather than aborting a 300-study fetch. |
| c | **Medium** | `taxonomy/reliability.py` | **CSV formula injection.** The annotation workflow has two people opening these files in a spreadsheet, and the cells carry LLM-generated rationales and verbatim registry text. A value beginning `=`, `+`, `-` or `@` is evaluated on open (`=WEBSERVICE`, `=HYPERLINK`, DDE via `=cmd|`). Fixed by prefixing a single quote on write, stripped again on read so agreement statistics are unaffected. |
| d | **Medium** | `models/llm_api.py` | **Prompt injection surface.** Arm 1 puts third-party registry prose into the prompt verbatim, and anyone can register a trial. Prompt v2 delimits quoted text, names it as data, and strips the delimiter from the source so it cannot close its own marker. This is a validity safeguard as much as a security one: an instruction-shaped criterion would be indistinguishable in the results from a reasoning failure. |
| e | **Medium** | `models/llm_api.py` | **Unstable cache key.** The key read `effective_parameters()`, which mutates the first time the API rejects a parameter — so the first item of a run was keyed differently from the rest, and the keys were racy under concurrency. Now keyed on the stable *requested* parameters, with the effective set recorded inside each entry. |
| f | Low | `data/loaders/ctgov.py` | Unbounded `json.load(resp)` in an unattended fetch loop. Capped at 64 MB, with an allowlist assertion that every fetched URL is under `API_BASE`. |
| g | Low | `leaderboard/submit.py` | A malformed submission raised `pydantic.ValidationError`, `TypeError` or `KeyError` — read as a toolkit bug rather than a rejected submission. Rewritten to raise `SubmissionError` naming the offending row, with size caps and duplicate-`item_id` detection. `score_submission` re-validates coverage so a gap cannot `KeyError` inside the runner. |
| h | Low | `data/atom_pool.py` | A corrupt or hand-edited pool file raised a bare `KeyError`. Now raises `AtomPoolUnavailable` with a rebuild instruction. A corrupt *cached study* is a hard error rather than a silent skip, because skipping one quietly changes the sampling frame. |
| i | Low | `eval/report.py`, `metrics/stats.py` | The report printed `n>=-1` where `-1` is the sentinel for "no difference to size"; `_z_from_power(1.0)` fell outside the quantile function's domain. Both guarded. |

## 14. The reported numbers are not re-runnable, only the experiment is

- **Status:** resolved-in-paper — **§7.3, Limitations, README, RUN.md and SECTION7.md corrected**
- **Problem.** The draft, the README and RUN.md said `--prompt-version 1` reproduces the
  reported numbers. It reproduces the *prompts*. The requested temperature of 0.0 was
  rejected by the model, so every completion used the API default, and the response cache
  is not redistributed. "Pinned dependencies, fixed seeds" invited a determinism claim that
  the one stochastic component in the pipeline does not support.
- **Resolution.** Item sets, gold labels and prompts are stated as deterministic;
  completions are not. The released `per_item_predictions` are named as the record of the
  run, and every aggregate in SECTION7.md is recomputed from them rather than carried
  forward. Added as a numbered limitation.

## 15. There was no path from results to the manuscript

- **Status:** resolved-in-code
- **Location:** `scripts/collect_paper_data.py` (new)
- **Problem.** v0.1 had `collect_paper_data.py` and `audit_paper_data.py`. Both were moved
  to `legacy/` in v0.2 because they imported removed modules, and neither was replaced — so
  the numbers in the manuscript were transcribed by hand from JSON with nothing checking
  them, which is the step where figures get mistyped.
- **Resolution.** One command produces `results/PAPER_DATA.md` (paste-ready tables matching
  the manuscript's section headings) and `results/paper_data.v2.json`. Every aggregate is
  recomputed from the persisted per-item predictions rather than copied from a stored
  aggregate, and the integrity gates from the v0.1 audit — ceiling effects, degenerate
  confidence, rationale clustering, unanswerable items, depth-trend significance with the
  per-pair n needed — run *as part of collection* rather than as a separate pass beside it.
  That closes v0.1 audit finding C9, where the prose discrepancy list had drifted two
  entries ahead of the machine-readable one.
- **`--verify` is the gate.** It diffs the numbers written in the manuscript against the
  computed ones and exits non-zero per mismatch. Validated by injecting five plausible
  transcription errors (a wrong accuracy, a wrong error count, transposed CI digits, a
  wrong ECE, a wrong rho) — all five were caught. It runs in CI, so the manuscript cannot
  silently drift from the artifacts.
- **Found by building it.** The collector immediately exposed a double-rounding
  inconsistency: rounding to four decimals and then formatting to three sends a value
  ending `.xxx5` the other way, so depth 3's ECE rendered as 0.171 in one artifact and
  0.170 in another. Rounding is now done once, from the raw value.

## 16. The committed manifest predates the `snapshot_id` field

- **Status:** open, cosmetic — **reported honestly rather than backfilled**
- **Location:** `data/ctgov_cache/MANIFEST.json`
- **Detail.** `write_manifest` now stamps a `snapshot_id`; the committed manifest was
  written before that, so the collector prints `snapshot unrecorded`. It is not backfilled
  because the atom pool file embeds a copy of the manifest, so editing one would desynchronise
  the two for no gain. The frame and the fetch date — which are what the contamination
  argument rests on — are both recorded. The id appears on the next rebuild.

## 17. Adjacent prior work by the same author — decided: omitted

- **Status:** resolved-in-paper — **decision made, closed**
- **Location:** manuscript §2 (related work)
- **The question.** The author has a topically adjacent preprint on AI-assisted oncology
  trial matching. The project plan required a decision: cite it properly as prior art, or
  leave it out entirely, and explicitly forbade a half-mention.
- **Decision.** **Left out entirely.** §2 makes no reference to it, and the related-work
  section stands on the seven external prior-art references it already cites.
- **Verification.** A full-tree sweep finds zero occurrences of the project name, its
  model, its pipeline description, or any derived count — in the code, the paper, the data,
  the docs or the audit trail. The atom pool and both arms are built by this repository's
  own ClinicalTrials.gov loader from the committed snapshot, so nothing is inherited from
  it implicitly either: no shared segmenter, no shared typing scheme, no shared counts.
- **Do not reopen this in review.** If a reviewer raises adjacent work, the answer is that
  §2 cites the external prior art that bears on the claims; it is not an omission to be
  patched with a late self-citation, which would produce exactly the half-mention the plan
  ruled out. Note separately that a journal's submission form may ask about related
  manuscripts by the same author — that is a disclosure question, distinct from the
  citation decision recorded here, and it is answered on the form rather than in §2.

## 18. Answerability was renderer-blind, which would have corrupted the v2 re-run

- **Status:** resolved-in-code
- **Location:** `criterialogic/taxonomy/annotate.py::unanswerable_reasons`
- **Problem.** The check took only the item, but answerability is a property of the item
  *and the renderer*: it fires when an atom asks about `CURRENT` and the record has the
  fact present-but-not-current, which is unanswerable **only** because renderer v1 omits
  the currency. Renderer v2 states it, so those items are answerable under v2 — but the
  flag would have kept firing, and `failure_breakdown` would have gone on withholding
  those errors from the taxonomy. In the v0.2 sweep that is 48 of 87 errors, so the v2
  run — the one performed specifically to remove this defect — would have reported a
  taxonomy distribution built on excluding the items it had just fixed.
- **Resolution.** `unanswerable_reasons(item, prompt_version)` returns empty for anything
  other than `"1"`. `run_task` reads the version off `model.info()` rather than assuming,
  so the offline diagnostics (no prompt at all, `prompt_version=None`) also correctly
  report nothing unanswerable. `prompt_version_assessed` is recorded in every taxonomy
  block. The collector pins the legacy runs to `"1"`, which is what they used.

---

## 19. Prompt-v1 sentences left behind by the v2 update

- **Status:** open — **the author decides the wording**
- **Location:** `paper/CriteriaLogic.md` §8 (discussion, first and second paragraphs), §7.7
  and §9; versus `results/compositional__openai.json::calibration` and
  `results/compositional__openai.json::metrics.by_depth`
- **Problem.** §7 was switched to the prompt-v2 `gpt-4o-mini` run, but four claims outside §7
  still describe the prompt-v1 `gpt-5-nano` run. They are not invented values — they were
  executed — but they are attributed to a run the paper no longer reports.
  1. §8 asserts a "flat region" that a natural corpus would sample. Under v2 there is none:
     depth 2 is 0.800 and depth 4 is 0.517.
  2. §8 claims per-depth triage at depth 5 ("0.717 to 0.917"). The v2 run persists a single
     pooled selective-accuracy curve over the depth 2–6 set and no per-depth curves, so no
     per-depth abstention claim can be derived from it. The pooled curve runs from 0.6033 at
     full coverage to 0.7926 at 10% coverage.
  3. §7.7 states a "0.35 accuracy range across depths". The v2 range is
     0.800 − 0.367 = 0.433.
  4. §9 lists the snapshot identifier among what every result file records. The value written
     is the placeholder `ctgov-unknown`.
- **Also open, and not numeric.** The abstract, contribution 3 and §5 state the two-annotator
  taxonomy in the completed tense while §7.5 reports that no human annotation exists. §6 still
  says GPT-4-class models returned `403 model_not_found` and that the adapter drops the
  requested temperature; both v2 runs record `effective_temperature: 0.0` and
  `dropped_parameters: []`.
- **What would resolve it.** Either scoring the depth sets separately, which would restore a
  per-depth abstention claim, or a wording pass. Paste-ready replacements are in
  `paper/DATA.md`, which is not committed.

## 20. Some Arm 1 forms misread their criterion, and the prompt does not say which governs

- **Status:** open — **the author confirms the verdicts and decides the wording**
- **Location:** `criterialogic/data/real_criteria.py::sentence_to_expression`;
  `criterialogic/models/llm_api.py::render_criterion`; `annotation/arm1_verification.csv`;
  `scripts/rescore_real_criteria.py`
- **Problem.** Raised by both reviewers. The v2 prompt shows the verbatim criterion and the
  mapped form together, with no instruction on which one governs, and the gold label follows
  the form. Entry 11 recorded that forms are partial readings; a criterion-by-criterion pass
  finds that some also change the meaning. "Patients younger than 8 years or older than 15
  years" maps to `age >= 8`; "not receiving dialysis" maps to `dialysis`; "First-time use of
  Crisugabalin Capsules" maps to `crisugabalin capsules`. On the first pass 126 of 463
  criteria are marked `drop`.
- **Resolution in code.** `scripts/rescore_real_criteria.py` re-scores the released
  predictions on the kept criteria, and separately without items whose label rests on the
  currency convention (entry 21). First-pass output: 0.965 [0.942, 0.980] on 376 items,
  against 0.935 on all 926. The mapper is not changed, so the released set still regenerates.

## 21. "Present, not currently active" is rendered for facts the oracle counts as met

- **Status:** open — mitigated, not removed
- **Location:** `criterialogic/data/synthetic.py::_sample_fact_for_atom` (sets `current` only
  for atoms with a `current` qualifier); `criterialogic/models/llm_api.py::render_patient` (v2
  states currency for every present finding); `criterialogic/oracle.py` (an untimed atom is met
  by any present fact)
- **Problem.** Every present fact for an atom with no time qualifier is rendered as "present,
  not currently active", and the oracle counts it as met. Against a present-tense criterion
  ("Receiving propofol for induction") a reader can reasonably answer not met. In the released
  Arm 1 run, 43 of the 60 errors involve such a fact (`metrics.structure.currency_ambiguous_leaves`).
- **Mitigation.** Arm 1: the headline subset excludes those items. Arm 2: about half of all
  leaves carry the convention in every released set; the size-matched set holds its count
  flat across depth (`results/size_matched/structure__*.md`), so it cannot drive a depth effect
  there. Removing it would change the prompt or the generator and invalidate the released runs.

## 22. Depth and expression size are confounded in the released compositional sets

- **Status:** resolved-in-code — **the author decides the wording**
- **Location:** `criterialogic/tasks/compositional.py::_build_expr`; versus manuscript §1, §3.4, §7.1-7.2
- **Problem.** Raised by both reviewers. `_build_expr` builds full trees with two or three
  operands per group, so leaves average 5.2 at depth 2 and 152.5 at depth 6; the item-level
  correlation between depth and log2(leaves) is 0.981 (sweep) and 0.973 (mixed set). No
  analysis of these sets can separate depth from size. At depth 6 the model answers "met" on
  0.97 of items against a gold met-rate of 0.40 (`results/depth_structure.md`).
- **Resolution in code.** `criterialogic/tasks/size_matched.py` holds leaves (14), groups (6),
  NOT nodes (4) and the gold base rate (0.5) fixed while depth runs 2-6, with AND/OR alternating
  so canonical depth equals nominal depth. `scripts/run_size_matched.py --model openai` runs it.
  The 4-5 point Spearman tests are supplemented by an item-level trend
  (`metrics.stats.item_level_trend`).
- **Result.** The size-matched `gpt-4o-mini` run (`results/size_matched/compositional__openai.json`,
  500 items) scores 0.72, 0.71, 0.65, 0.66 and 0.70 at depths 2-6: no decline with depth at
  fixed size. The claim the manuscript can make moves from depth to expression size; the
  author decides the wording.

## 24. The size claim needs size varied at fixed depth

- **Status:** resolved-in-code — run complete; **the author decides the wording**
- **Location:** `criterialogic/tasks/size_matched.py::generate_size_sweep_items`;
  `scripts/run_size_sweep.py`
- **Problem.** Entry 22's result moves the manuscript's claim to expression size, but in the
  released sets size was only ever varied together with depth.
- **Resolution in code.** A converse set holds depth at 3 while leaves double from 7 to 112,
  with groups and NOT nodes in the size-matched ratio and the gold label half met at every
  size; its 14-leaf level is the size-matched depth-3 configuration drawn again. The trend is
  reported per doubling of leaves.
- **Result.** The `gpt-4o-mini` run (`results/size_sweep/compositional__openai.json`, 500 items)
  scores 0.70, 0.67, 0.58, 0.58 and 0.53 at 7, 14, 28, 56 and 112 leaves; odds ratio per
  doubling of leaves 0.833 [0.732, 0.948], likelihood-ratio p = 0.0052, permutation p for a
  decline 0.0024 (`results/size_sweep/structure__openai.md`). Its 14-leaf level scores 0.67,
  against 0.71 for depth 3 in the size-matched set.

## 23. Inter-annotator agreement falls once Arm 1 label artefacts are removed

- **Status:** open — **the author decides the wording**
- **Location:** `scripts/rescore_real_criteria.py`; versus manuscript §5, §7.5, §11
- **Problem.** 47 of the 60 Arm 1 errors that were annotated fall outside the verified
  headline subset (entries 20-21), so they are not established model failures. Removing them
  leaves 132 errors with kappa 0.165 [0.068, 0.266], against 0.337 [0.252, 0.420] on all 179;
  the compositional arm alone is unchanged at 0.088.

## 25. Repository metadata still described the submitted manuscript

- **Status:** resolved-in-code
- **Location:** `CITATION.cff`; `pyproject.toml`; `criterialogic/data/loaders/ctgov.py::_USER_AGENT`;
  `README.md`; `Makefile::release`; versus the manuscript title and §9
- **Problem.** `CITATION.cff`, `pyproject.toml` and the snapshot fetcher's user agent gave the
  repository as `github.com/darogyasami/criterialogic`, not the
  `github.com/DanielMartin-Arogyasami/criterialogic` that §9 cites, and the release gate looked
  only for the literal placeholder. `CITATION.cff` and `pyproject.toml` carried the submitted
  title and description, and the README presented the decline as an effect of depth and Arm 1
  at 0.935 on all 926 items, which the revised manuscript no longer claims (entries 20, 22).
  The README also attributed the missing snapshot id in the compositional run to its date;
  the compositional generator never records one and identifies its source by the atom pool
  digest instead.
- **Resolution in code.** Title, description and URLs corrected; version 0.3.0. The README
  reports the size-matched set, the size sweep and the verified Arm 1 subset beside the
  original figures. `make release` now also fails on the stale handle, and no longer passes
  without checking anything when `paper/` is absent.

## 26. Supplement S3 did not contain the revision's tables

- **Status:** resolved-in-code
- **Location:** `scripts/assemble_supplement.py::assemble_s3`; versus manuscript §14 (S3)
- **Problem.** The revised manuscript describes S3 as per-depth and per-size tables for every
  run, the size-matched set and the size sweep included, with their structure tables. The
  assembler copied only the original runs' tables from `results/paper_data.md` and listed only
  the original run files. The copied headings carried the submitted manuscript's section
  numbers, and the summary line pointed to integrity gates that S3 left out.
- **Resolution in code.** S3 embeds `results/depth_structure.md`, the size-matched and
  size-sweep structure tables and `results/real_criteria_verified.md`; lists all four item
  sets and every run file; renumbers the copied headings (mixed set §7.1, renderer check
  §7.8); and includes the integrity gates. Text the assembler expects but cannot find fails
  loudly.
