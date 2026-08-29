# CriteriaLogic — remaining work, specified for Cursor

Hand these to Cursor **one work item per session**. Do not paste the whole file as a single
prompt; the items have different blast radii and W0 must be understood before any of the others
are attempted.

Repo assumptions: package `criterialogic`, collection script `collect_paper_data.py`, results in
`results/`, LLM response cache in `.criterialogic_cache/`.

---

## W0 — Standing guardrails (read before every other item)

Put this block at the top of every Cursor prompt in this project. It is the single most
important instruction here, because the failure mode is not bad code, it is a model helpfully
inventing an experimental result.

> **Standing rules for this repository.**
>
> 1. **Never write a number into the paper, into `results/`, or into any docstring, comment,
>    README, or test that was not produced by executing code on real data.** Section 7 of the
>    manuscript uses `[…]` brackets deliberately. If you cannot compute a value, leave the
>    bracket. Do not "illustrate" with a plausible figure. Do not fill a placeholder to make a
>    table render.
> 2. **Never generate example outputs that look like measurements.** If you need a fixture,
>    name it `fixture_`/`synthetic_` and make the provenance obvious in the filename and in the
>    data itself.
> 3. **Every metric that touches synthetic data must carry a provenance flag through to the
>    output**, so that no downstream reader can mistake a synthetic-patient result for an n2c2
>    result.
> 4. **If a data source is absent, fail loudly.** Raise with a message naming the missing path
>    and how to obtain it. Never silently fall back to synthetic data, and never `except: pass`
>    around a missing corpus.
> 5. **Do not modify the manuscript's scientific claims.** If code reveals that a claim is
>    wrong, add it to `results/DISCREPANCIES.md` and stop. The author decides the wording.
> 6. Ask before adding a dependency. Pin anything you add.

---

## Priority order

| # | Item | Unblocks | Can Cursor do it alone? |
|---|---|---|---|
| W1 | ClinicalTrials.gov atom pool | Fixes discrepancy #1 | Yes |
| W2 | Chia ingestion + splits | Tasks A, B | Yes |
| W3 | Task A structuring | §7.1 row | Yes |
| W4 | Task B typing/polarity | §7.1 row | Yes |
| W5 | n2c2 real-data adapter | §7.1 Task C (real) | Code yes, data no |
| W6 | Provider layer + inference-param fidelity | §6, §9 | Yes |
| W7 | Encoder baselines | §6 ladder | Yes, needs compute |
| W8 | Local open-weight runner | §6 ladder | Yes, needs compute |
| W9 | Ablation harness | §7.5 | Yes |
| W10 | Reliability tooling | §5 κ values | Tooling yes, labels no |
| W11 | Depth-trend statistics | Fixes discrepancy #2 | Yes |
| W12 | Fix `collect_paper_data.py` | Integrity of the artifact | Yes |
| W13 | Release hygiene | §9 | Yes |

---

## W1 — Build a real ClinicalTrials.gov atom pool

**Why.** `collect_paper_data.py` already flags this: the paper says Task D atoms come from real
ClinicalTrials.gov criteria, but `tasks/compositional.py::_atom_pool` derives them from the leaf
predicates of the 13 n2c2 criteria, and the `CTGOV_SYNTHETIC` source enum makes that harder to
notice. Right now the paper describes a data source the code never touches.

**Prompt for Cursor:**

> Create `criterialogic/data/ctgov.py`.
>
> - Fetch eligibility criteria from the ClinicalTrials.gov **v2** REST API. Base URL is
>   `https://clinicaltrials.gov/api/v2/`. Pagination is cursor-based via `pageToken`, **not**
>   `min_rnk`/`max_rnk`. The v1 API is retired and `api.clinicaltrials.gov` no longer resolves —
>   do not write against it.
> - Eligibility text lives in `protocolSection.eligibilityModule.eligibilityCriteria` as a
>   single free-text blob. Fields can be absent; never assume a key exists.
> - Query Phase-IV interventional studies to match Chia's sampling frame. Record the exact query
>   parameters used in the cache manifest.
> - Cache raw JSON responses to `data/ctgov_cache/` keyed by NCT ID. Never re-fetch on a cache
>   hit. Rate-limit to at most 2 requests/second.
> - Add `scripts/fetch_ctgov_atoms.py` that populates the cache and writes
>   `data/ctgov_atom_pool.json` with, per atom: the atom, the source NCT ID, the verbatim source
>   sentence, and the fetch timestamp.
> - Rewrite `tasks/compositional.py::_atom_pool()` to read that file. If it is missing, raise
>   with instructions to run the fetch script. Do not fall back to the n2c2 leaves.
> - Split the source enum into `CTGOV` (real text) and `N2C2_DERIVED` (current behaviour), and
>   make every generated item record which one it used.
> - Prefer trials first posted **after** the training cutoffs of the evaluated models, and record
>   the posting date per atom, so §3.5's contamination claim has evidence behind it.
>
> Acceptance: `pytest` passes offline using a checked-in cached fixture of ≤5 NCT records; a
> generated Task D item carries a resolvable NCT ID back to verbatim source text; regenerating
> with the same seed and the same cache is byte-identical.

**Then update `results/DISCREPANCIES.md`** to record that discrepancy #1 is resolved in code, and
flag §3.4 of the manuscript for a wording check by the author.

---

## W2 — Ingest Chia and build leakage-checked splits

**Why.** Chia is the "fully releasable" backbone of the benchmark and Tasks A and B do not exist
without it. It is permissively licensed and there is no access barrier — this is the single
largest unblock available today.

**Sources:** figshare `Chia Annotated Datasets` (article 11855817), or the `bigbio/chia`
mirror on Hugging Face. Format is brat standoff: paired `.txt` / `.ann` files, 15 entity types,
12 relation types. Note that Chia ships in two variants (with and without the `Scope` relation);
pick one, document the choice, and do not mix them.

**Prompt for Cursor:**

> Create `criterialogic/data/chia.py`.
>
> - `download_chia(dest)` — fetch and verify by checksum. Record the source URL and the SHA256
>   in `data/chia/MANIFEST.json`. Do not commit the corpus itself; add it to `.gitignore`.
> - `parse_brat(txt_path, ann_path) -> ChiaCriterion` — parse standoff into typed entities,
>   relations, and attributes. Preserve character offsets.
> - `to_logical_form(criterion) -> LogicalForm | UnmappableCriterion` implementing the §3.2
>   mapping: entities → `Entity`, AND/OR relations → `BooleanGroup`, negation relation → `Not`
>   wrapper, value relations → `NumericConstraint`, temporal relations → `TemporalConstraint`.
> - **Do not force a mapping.** When a criterion cannot be represented in schema v0.1 (cardinality,
>   `Scope` semantics, cyclic annotation graphs, dangling relation endpoints), return
>   `UnmappableCriterion` with a machine-readable reason code.
> - `scripts/build_chia_dataset.py` writes harmonized records plus
>   `results/chia_coverage.json` reporting: total criteria parsed, count mapped, count unmappable
>   by reason code, and the distribution of nesting depth and node types across mapped forms.
>
> Acceptance: round-trip test (`brat → LogicalForm → JSON → LogicalForm`) is lossless for mapped
> criteria; all intrinsic validators from `schema/logical_form.py` pass on every emitted record;
> the coverage report is deterministic across runs.

**Second prompt, same item:**

> Create `criterialogic/data/splits.py`.
>
> - Trial-keyed train/dev/test split (§3.5) so no NCT ID straddles a boundary. Deterministic
>   given a seed; write the assignment to `data/splits/chia_splits.json`.
> - `verify_no_leakage(splits) -> LeakageReport` checking trial-ID disjointness **and**
>   near-duplicate criterion text across splits (normalized-text hash plus a similarity check).
> - A test that fails if any trial ID or duplicate criterion text appears in two splits.

The coverage percentage from `chia_coverage.json` is a real, citable number about the schema and
belongs in the manuscript. Do not let Cursor guess it in advance.

---

## W3 — Task A: structuring

> Implement `criterialogic/tasks/structuring.py` and `criterialogic/metrics/structuring.py`.
>
> Metrics, from first principles, no hidden dependencies:
> - **Entity F1** — set-based over (type, normalized span) tuples. Implement strict (exact
>   offsets) and relaxed (overlap) variants; report both.
> - **Relation F1** — set-based over (head, relation type, tail).
> - **Logical-form exact match** — apply `canonicalize` to both gold and prediction first, then
>   compare. Per §3.1 this is what makes exact match meaningful.
>
> Implement `models/structuring_llm.py`: prompt an LLM to emit JSON conforming to the schema,
> validate with pydantic, and **count parse failures as a separate reported category** rather
> than as wrong answers. A model that emits invalid JSON 30% of the time is a different finding
> from one that emits valid but wrong structure — the manuscript needs both numbers.
>
> Acceptance: gold-vs-gold scores 1.0 on all three metrics; a hand-built perturbation suite
> (dropped negation, flipped operator, reordered operands) produces the expected metric
> movements, and reordering alone scores 1.0 exact match.

---

## W4 — Task B: typing and polarity

> `criterialogic/tasks/typing_polarity.py` is currently a task-name contract only. Implement it.
>
> - Derive labels from the harmonized Chia records: entity type (15 classes), criterion polarity
>   (inclusion/exclusion), presence of temporal qualifier, presence of numeric qualifier.
> - Report macro-F1 and per-class precision/recall/F1, plus the class support counts — several
>   Chia entity types are rare and a macro average over a class with n=3 needs to be visible as
>   such.
> - Emit a confusion matrix to `results/task_b_confusion.json`.
>
> Acceptance: label counts in the emitted dataset reconcile exactly against `chia_coverage.json`.

---

## W5 — n2c2 adapter, written before the data arrives

**Why.** The DUA has the longest lead time of anything on this list. Write the adapter now so the
data is a drop-in when access is granted, and so nothing about the real run is blocked on code.

Reference facts for the spec: 288 patients, 2–5 notes each, partitioned into 202 train / 86 test,
13 criteria, XML with per-criterion `met`/`not met` tags.

> Create `criterialogic/data/n2c2.py`.
>
> - `load_n2c2(root)` parsing the official XML into `(patient_id, notes, {criterion_tag: label})`.
> - If `root` does not exist, raise `N2C2DataUnavailable` with the DUA URL
>   (`https://portal.dbmi.hms.harvard.edu/projects/n2c2-2018-t1/`) and the expected directory
>   layout. Never substitute synthetic patients.
> - Ship `tests/fixtures/n2c2_synthetic/` — 3 fake patients in the **exact real XML format**, so
>   the full test suite runs without the DUA. Every file must contain an unmissable
>   `SYNTHETIC — NOT REAL PATIENT DATA` marker.
> - Add `.gitignore` and a pre-commit hook that blocks committing anything under the real n2c2
>   data path.
>
> Separately: §4 of the manuscript says exact parity with the official n2c2 scorer is "pending."
> Resolve it. Obtain the official scorer, run both on identical predictions over the synthetic
> fixture, and assert equality in a test. If they differ, document the difference precisely in
> `results/DISCREPANCIES.md` — do not quietly adopt whichever is more convenient.

---

## W6 — Provider layer and inference-parameter fidelity

**Why.** Two real problems. Only `gpt-5-nano` is reachable, and a 403 currently kills a run
rather than being recorded. And the temperature was requested at 0.0 but silently dropped, so the
manuscript's §6 promise to report inference parameters is not currently satisfiable for the one
real model in the study.

> Refactor `criterialogic/models/llm_api.py` into a provider layer.
>
> - Support multiple providers behind one interface. Read credentials from env vars only; never
>   hardcode or log a key.
> - `probe_models()` returns which model IDs the current credentials can actually reach. Write
>   the result to `results/model_access.json`, including the failure reason (403
>   `model_not_found`, rate limit, etc.) for the unreachable ones. An inaccessible model must be
>   a recorded row, not a crash.
> - **Record requested vs. effective inference parameters per call**, in the cache entry itself:
>   what was sent, what the API rejected, what was actually used. The current
>   silent-drop-then-forget behaviour is exactly the gap that makes the run non-reproducible.
> - Cache entries must key on `(model_id, prompt_hash, effective_params)`. Changing a parameter
>   must invalidate the cache. Write `.criterialogic_cache/MANIFEST.json` with entry count,
>   model IDs, and creation timestamps.
> - Add `--no-cache` and `--cache-only` flags. `--cache-only` must fail loudly on a miss rather
>   than making a live call, so collection passes cannot incur surprise spend.

---

## W7 — Encoder baselines

`models/encoder.py` currently raises `NotImplementedError`.

> Implement a fine-tuning harness for BioClinicalBERT, PubMedBERT, and BioBERT on Tasks B and C.
>
> - Config-driven (model ID, LR, epochs, batch size, max length, seed) with configs checked in.
> - Fixed seeds; log the resolved config and the git SHA into every checkpoint directory.
> - Train on the Chia train split only; never touch test.
> - Add `--smoke` mode that trains on 20 examples for 1 step, so CI verifies the path without a GPU.
>
> Do not report a metric from a smoke run anywhere.

---

## W8 — Local open-weight runner

`models/llm_local.py` is a stub.

> Implement a local runner (HF `transformers`, optional vLLM backend) for the Llama-3.x, Mistral,
> and Qwen families. Same `Model` interface as the API models, so `run_task` is unchanged.
> Confidence must come from token logprobs where available; if a model cannot supply a
> calibrated confidence, it must declare that rather than returning a constant — a constant 1.0
> would silently corrupt every ECE number in §7.4.

---

## W9 — Ablation harness (§7.5)

> Create `criterialogic/eval/ablations.py` and `scripts/run_ablations.py`.
>
> Sweep three axes independently: prompt variant (≥3 designs, checked in verbatim for supplement
> S3), few-shot count (0, 1, 3, 5), retrieval on/off. Write one row per
> (model, task, axis, setting, seed) to `results/ablations.jsonl`.
>
> Run every cell at ≥3 seeds and report mean and spread. A single-seed ablation delta is not
> reportable and the harness should not make it easy to produce one.

---

## W10 — Reliability tooling for the taxonomy (§5)

**Why.** §5's entire argument for single-annotator credibility rests on two numbers — human-vs-
automatic κ and test–retest κ — and neither exists. Cursor can build the tooling; only the author
can produce the labels.

> Implement `criterialogic/taxonomy/reliability.py`:
> - Cohen's κ with a bootstrap 95% CI, plus raw percent agreement.
> - Per-category agreement and a full confusion matrix (human × heuristic).
> - `disagreements()` returning every case where the labels differ, with the item text, both
>   labels, and the model's rationale, so each one can be inspected as §5 promises.
> - Test–retest κ over two human passes of the same subset.
>
> Improve the CSV round-trip: `scripts/export_for_annotation.py` writes one row per error with a
> blank `human_category` and a `pass_id` column; `scripts/import_annotations.py` validates that
> every category string is in the codebook, that no row is blank, and that item IDs still resolve.
>
> Add a **blinding** option that shuffles row order and hides the heuristic label, so the human
> pass is not anchored by the automatic one. Without it the κ is inflated and the reviewer will
> say so.
>
> Acceptance: κ = 1.0 on identical label sets; κ ≈ 0 on shuffled ones; every reported κ carries
> its CI and n.

---

## W11 — Depth-trend statistics (discrepancy #2)

> The manuscript hypothesizes accuracy declines monotonically with nesting depth; the 36-item set
> (12 per depth) cannot resolve that. Add `criterialogic/metrics/trend.py`:
> - Spearman rank correlation between depth and accuracy, with a p-value.
> - Wilson score intervals on the per-depth accuracies.
> - A power calculation reporting the n-per-depth needed to detect a given effect at 80% power.
>
> Have `collect_paper_data.py` print the required n alongside the observed curve, so §7.2 either
> reports an adequately powered result or states the limitation with a number attached.

---

## W12 — Repair `collect_paper_data.py`

Concrete defects in the current file:

> 1. **Lines 172–173:** `tests_passing: 33` and the lint result are hardcoded string literals in
>    the reproducibility block. Replace with actual subprocess invocations of `pytest --tb=no -q`
>    and `ruff check .`, parsing real output. A hardcoded test count in a reproducibility artifact
>    will go stale silently and is exactly the kind of thing a reviewer checks.
> 2. **Line 124:** `llm.predict_batch(items)` is called a second time purely to attach heuristic
>    categories, after `evaluate()` already called it. Reuse the predictions from the first call.
>    On a cache miss this currently doubles API spend.
> 3. **Provenance flags:** every row in `paper_data.json` needs explicit
>    `patients: synthetic | real_n2c2` and `atoms: n2c2_derived | ctgov` fields. The integrity
>    banner in the markdown is good but does not survive into the JSON, and the JSON is what
>    someone will script against.
> 4. **Oracle labelling:** mark the `rule_based` rows `is_oracle: true` in the data structure
>    itself, not only in prose, so no downstream table can present it as a competitive system.
> 5. **Cache dependency:** fail with a clear message if `.criterialogic_cache/` is missing or its
>    manifest does not match the requested model, instead of silently making live calls.
> 6. **Task A/B rows:** once W2–W4 land, add them; until then keep them in `cannot_fill`.

---

## W13 — Release hygiene (§9)

> - `DATASHEET.md` following Gebru et al. (2021), covering composition, collection, preprocessing,
>   uses, distribution, maintenance. §S4 of the manuscript promises this file.
> - `criterialogic/leaderboard/` — submission schema, a validator asserting a submission covers
>   exactly the evaluated item set, and a scorer reusing the same `run_task` runner as the
>   baselines.
> - `CITATION.cff`, `LICENSE` (MIT), and a `NOTICE` recording the licence terms inherited from
>   Chia and the DUA terms governing n2c2.
> - Pin every dependency with hashes. Add a `make reproduce` target that runs the full pipeline
>   from a clean checkout.
> - Publish prompts verbatim to `supplement/S3_prompts/` (manuscript §S3).

---

## Not delegable — author only

Cursor cannot do these, and none of the Task C or §5 numbers in the manuscript exist until they
are done.

1. **Submit the n2c2 DUA** at `https://portal.dbmi.hms.harvard.edu/projects/n2c2-2018-t1/`.
   Longest lead time on the list. Start it before writing any more code.
2. **Obtain API access to at least two more model families.** The current project reaches only
   `gpt-5-nano`, which is not the "ladder of systems" §6 describes.
3. **Do the taxonomy annotation pass**, then the washout re-labelling. §5 is unsupported until
   both κ values exist.
4. **Decide the §3.4 wording** once W1 lands, and the §7.2 wording once W11 reports the observed
   trend.
5. **Finalize affiliation, correspondence, and the S5 AI-assistance disclosure** per venue policy.
6. **Resolve references 8–10** and confirm the Gebru et al. DOI (manuscript §12 flags these).

---

## Working notes for Cursor sessions

- One work item per session. W2 and W5 will each blow a context window if bundled with anything.
- Start each session by pasting **W0**, then the single item.
- After each item: run the full test suite, run `collect_paper_data.py`, and diff
  `results/paper_data.json` against the previous run. An unexplained numeric change is a bug
  until proven otherwise.
- Any time Cursor proposes text for the manuscript, treat it as a draft for the author, not a
  commit. The manuscript is the one artifact where an invented number is misconduct rather than a
  bug.
