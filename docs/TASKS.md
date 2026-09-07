# Remaining tasks

Five cards. Each names the files to open and what "done" means. **Attach one card and the
files it names — never the repo.** Most of the work is `make` targets that need no agent.

**Order matters, and it changed.** T1 gates everything. T2 supersedes the current numbers.
**T4 (second model) now comes before T3 (annotation)**: the error pool is 87 against an
annotation floor of 150, and at 87 the kappa interval spans three agreement bands, so the
labelling would cost ~10 person-hours and support no claim. Three models at n=60/depth gives
~165 errors. The canonical sequence is in `CURSOR_START.md`.

---

## T1 — First real execution · no agent needed

Nothing in this repo has ever run against real pydantic. This is the moment of truth.

```bash
make setup
make check PY=./.venv/bin/python
```

**Done when** `preflight.py` prints all PASS, `pytest -q` is green, `ruff check .` is clean.

**If something fails:** preflight names the check and the fix. The three most likely to
break, because they are the least exercised: `test_end_to_end.py::test_real_criteria_segmentation_yields_forms`,
`::test_real_criteria_pipeline_runs`, and `test_taxonomy.py::test_temporal_probe_fires_on_a_nested_criterion`.

**Only if a test fails, give the agent:** the failing test name, the traceback, and the one
module it points at. Not the suite.

---

## T2 — Fill Section 3, then re-run under prompt v2

### T2a · no agent needed

```bash
make data
```

Prints Arm 1's criteria count, mapping rate, polarity split and depth histogram. These are
the `[N criteria from [N] trials...]` brackets in §3.2.

**Watch for `criteria_mapped_coordinated: 0`.** If it is zero, Arm 1 is entirely
single-predicate at depth 0, and §3.2 must say so plainly instead of describing the
coordination path as if it fires. Pool analysis says ≥93% depth-0 is likely.

### T2b · needs `OPENAI_API_KEY`, no agent tokens

```bash
export OPENAI_API_KEY=...
make run-llm
make paper verify
```

This is the single highest-value remaining experiment. Prompt v2 fixes the currency
rendering defect (§7.3's confound) **and** the exclusion-polarity ambiguity — and Arm 1 is
invalid under v1, because v1 asked an ambiguous question about exclusion criteria, which
is most of Arm 1.

**Expect the numbers to change, and report whatever they are.** The depth threshold may
soften or move. If the effect weakens, that is the result.

**Then edit `paper/CriteriaLogic.md`:** paste the tables from `results/PAPER_DATA.md` into
§7.1–7.5, and update §7.3 to say the confound is removed rather than bounded. `make verify`
must exit 0.

**Files for the agent, if used:** `results/PAPER_DATA.md` + the specific §7 subsection
being edited. Do not attach the whole paper.

---

## T3 — Annotation · humans, not an agent

**Do T4 first.** Blocked on the error pool: 87 available, 150 needed. The codebook is written, so nothing
blocks you. `docs/CODEBOOK.md` is the instrument — read it before labelling anything.

1. **Calibration session.** Twenty errors labelled together, every disagreement discussed,
   codebook revised where the *wording* was at fault. Record the revision in the codebook's
   §6 history. **Discard those twenty** — they do not enter the statistics.
2. `make annotate-export` — writes two blind CSVs plus a held-back automatic-label file.
3. Both annotators fill `category` and `clinical_judgement_required`, independently, from
   the codebook. Neither sees the other's file or the automatic labels.
4. `make annotate-report`, then fill `resolved_category` for **every** row of
   `annotation/adjudication.csv` (the code refuses to produce a consensus otherwise), then:

```bash
python scripts/annotation_report.py --a annotation/errors_annotator1.csv \
  --b annotation/errors_annotator2.csv --adjudication annotation/adjudication.csv \
  --automatic annotation/automatic_labels_HELD_BACK.csv --out results/agreement.json
```

`make paper` then picks up `results/agreement.json` and fills §7.5.

**Publish whatever kappa comes out.** A low figure is a real finding about how hard error
attribution is, and it bears on whether taxonomy-based error analysis is a reliable
instrument at all. Do not relabel after seeing the number.

**Also decide:** if annotator 2 labels 200 items and contributes to the codebook,
co-authorship is defensible. Have that conversation *before* the annotation.

---

## T4 — Second and third model · small agent task · **do before T3**

One evaluated system is the paper's weakest point, and it also blocks the annotation: it
fixes the single-model limitation *and* fills the error pool from 87 to ~165. It is an
access problem, not an engineering one. OpenRouter or Together serve Llama/Qwen/Mistral for cents against the
same interface.

**Task:** add one adapter subclassing `Model` with a `predict(item) -> Prediction` method,
register it in `criterialogic/models/__init__.py::REGISTRY`, then `make run-llm` with it.

**Files:** `criterialogic/models/base.py`, `criterialogic/models/llm_api.py` (as the
worked example), `criterialogic/models/__init__.py`. Three files, ~600 lines.

**Must:** reuse `system_prompt(prompt_version)` and `render_criterion` / `render_patient`
from `llm_api` — a different prompt makes the comparison meaningless. Report the parameters
the API *applied*, not the ones requested.

**Done when** two systems appear in `results/PAPER_DATA.md` and the README leaderboard
table, each with its Wilson interval.

---

## T5 — Release · no agent needed

```bash
make release
```

Fails if a placeholder survives. Before it passes, fill by hand:

- `[GITHUB-HANDLE]` — currently `darogyasami`, in `README.md`, `pyproject.toml`,
  `CITATION.cff`, and the user-agent string in `criterialogic/data/loaders/ctgov.py`.
- `[email]` in `paper/CriteriaLogic.md`.
- **References 8 and 9** — arXiv preprints located by content, author lists *unconfirmed*,
  cited for substantive claims. Verify both and check for published versions.

Then:

1. Post to medRxiv.
2. Two Zenodo deposits — the repository and the snapshot **separately**, so the data can be
   cited independently of the code. Put both DOIs in `CITATION.cff`.
3. Submit. Check the article processing charge before committing: *Scientific Data* is fully
   open access, so the charge is mandatory; JAMIA and JBI are hybrid, so a
   subscription-model publication costs nothing. If the charge is prohibitive that is an
   argument for JAMIA first rather than as the fallback.
4. **Set the 60-day deadline now** for moving to the next venue on rejection, so a
   rejection does not become a stall.

---

## If time runs out

Minimum publishable version: compositional arm only, one model, prompt v2, no human
annotation, taxonomy reported as heuristic with the reachability caveat stated. That still
contains the actual contribution — the depth threshold — and it is honest. Ship it rather
than stalling for the complete version.
