# CriteriaLogic — operating manual

Single source of truth for what to run, in order. Windows PowerShell is primary (`make`
targets given as shortcuts where you have Git Bash or WSL).

## Rule zero: do not paste code into chat

The code is on disk and Cursor reads it. `CriteriaLogic-v0.2-combined.md` is for **human**
review — pasting it costs ~115k tokens to tell the agent what it can read itself.
`.cursorignore` keeps ~352k of the repo's ~490k tokens (snapshot, atom pool, result JSON,
legacy scripts) out of context. Do not delete it. Read summaries instead of sources:
`data/README.md` for the snapshot, `results/PAPER_DATA.md` for results.

Almost nothing below needs the agent. It is a command runner, not a reasoning problem.

## The sequence

| Phase | What | Agent? | Blocking |
|---|---|---|---|
| 0 | Setup | no | — |
| 1 | Verify it runs | only on failure | everything |
| 2 | Fill Section 3 | no | §3.2 |
| 3 | Re-run under prompt v2 | no | all of §7 |
| 4 | Add 2 more models | **yes, small** | phase 6 |
| 5 | Update the paper | small edits | submission |
| 6 | Annotation | humans | §7.5 only |
| 7 | Release | no | — |

---

## Phase 0 — setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

On the corporate network, point pip at your organisation's index first
(`pip config set global.index-url <index>`), not PyPI.

Open the **folder** in Cursor (not individual files). Attach only this file to chat.

## Phase 1 — verify it runs

```powershell
python scripts/preflight.py
python -m pytest -q
python -m ruff check .
```
`make check`

**Done when** preflight is all PASS, pytest green, ruff clean.

Nothing here has ever executed against real pydantic, so expect a shakeout. **This is the
one place to use chat:** attach the failing test name, the traceback, and the single module
it points at. Not the suite.

## Phase 2 — fill Section 3

```powershell
python scripts/build_real_criteria.py --stats
```
`make data`

Prints Arm 1's criteria count, mapping rate, polarity split and depth histogram — the
`[N criteria from [N] trials...]` brackets in §3.2.

**Read `criteria_mapped_coordinated`.** If it is `0`, Arm 1 is entirely single-predicate at
depth 0, and §3.2 must say so plainly rather than describing the coordination path as if it
fires. Pool analysis suggests ≥93% depth-0.

## Phase 3 — re-run under prompt v2

```powershell
$env:OPENAI_API_KEY="sk-..."
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model openai --outdir results
python scripts/run_eval.py --task real_criteria --model openai --outdir results
python scripts/collect_paper_data.py
```
`make run-llm && make paper`

v2 is the default and fixes two things: the currency-rendering confound (§7.3) and the
exclusion-polarity prompt ambiguity. **Arm 1 is invalid under v1**, because v1 asked an
ambiguous question about exclusion criteria and that is most of Arm 1.

**Expect the numbers to change; report whatever they are.** The depth threshold may soften
or move. A weaker effect is the result, not a failure.

## Phase 4 — add two more models

Everything currently rests on one system, and that is the paper's biggest weakness. It also
blocks phase 6: the error pool is **87 errors** against an annotation floor of 150. Three
models at n=60/depth gives ~165. One job, two problems.

**Agent task.** Subclass `Model` with `predict(item) -> Prediction`, register it in
`criterialogic/models/__init__.py::REGISTRY`. Attach: `models/base.py`, `models/llm_api.py`
(the worked example), `models/__init__.py`. Three files.

**Must** reuse `system_prompt(prompt_version)`, `render_criterion` and `render_patient` from
`llm_api` — a different prompt makes the comparison meaningless — and report the parameters
the API *applied*, not those requested. OpenRouter or Together serve Llama/Qwen/Mistral for
cents.

```powershell
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model <name> --outdir results
python scripts/collect_paper_data.py
```
`make run-llm MODEL=<name>`

**Done when** `results/PAPER_DATA.md` and the README leaderboard show three systems, each
with its Wilson interval.

## Phase 5 — update the paper

`results/PAPER_DATA.md` headings map 1:1 onto the manuscript's. Copy, never retype.

| From `PAPER_DATA.md` | Into `paper/CriteriaLogic.md` |
|---|---|
| Section 3 bullets + Arm 1 block | §3.2 (replaces the brackets) |
| §7.1 table | §7.1 table — drop the Seed column or keep it, the verifier accepts both |
| §7.1 prose (pooled, rho, p, CI-separated, unresolved pairs) | §7.1 prose — **update the prose too** |
| §7.2 table + prose | §7.2 |
| §7.3 table | §7.3 — and rewrite the text: the confound is *removed*, not bounded |
| §7.4 table | §7.4 |
| §7.5 table | §7.5 (human numbers stay bracketed until phase 6) |
| — | §7.6 Arm 1 model rows |
| Integrity gates | Limitations — every BLOCK becomes a stated limitation |

Also update the abstract and §11, which quote the headline figures, and §6 (one system
becomes three).

```powershell
python scripts/collect_paper_data.py --verify
```
`make verify` — **must exit 0.** It catches wrong accuracies, error counts, transposed CI
digits, wrong ECE, wrong rho.

## Phase 6 — annotation

Humans, ~10–16 person-hours. Read `docs/CODEBOOK.md` first; it is the instrument.
**Do not start before phase 4** — at 87 errors the kappa interval spans three agreement
bands and supports no claim.

1. **Calibration session**: 20 items labelled together, disagreements discussed, codebook
   revised where the *wording* was at fault (record it in the codebook's §6). **Discard
   those 20.**
2. `make annotate-export` — two blind CSVs plus a held-back automatic-label file.
3. Both annotators fill `category` and `clinical_judgement_required`, independently.
   Neither sees the other's file or the automatic labels.
4. `make annotate-report`, then fill `resolved_category` for **every** row of
   `annotation/adjudication.csv` — the code refuses a consensus otherwise. Then:

```powershell
python scripts/annotation_report.py --a annotation/errors_annotator1.csv `
  --b annotation/errors_annotator2.csv --adjudication annotation/adjudication.csv `
  --automatic annotation/automatic_labels_HELD_BACK.csv --out results/agreement.json
```

`make paper` then fills §7.5. **Publish whatever kappa comes out** and do not relabel after
seeing it. Decide co-authorship for annotator 2 *before* the labelling, not after.

## Phase 7 — release

```powershell
python scripts/collect_paper_data.py --verify
```
`make release` — fails if a placeholder survives.

Fill by hand: `[GITHUB-HANDLE]` (currently `darogyasami`, in `README.md`, `pyproject.toml`,
`CITATION.cff`, and the user-agent in `data/loaders/ctgov.py`); `[email]` in the paper;
and **verify references 8 and 9** — arXiv preprints, author lists unconfirmed, cited for
substantive claims.

Then: medRxiv → two Zenodo deposits (repository and snapshot **separately**, so the data is
citable independently) → DOIs into `CITATION.cff` → submit. Check the article processing
charge first: *Scientific Data* is fully open access so the charge is mandatory, while JAMIA
and JBI are hybrid and cost nothing on the subscription route. **Set the 60-day next-venue
deadline now.**

---

## Two rules that get broken most

Both are in `.cursorrules`, which loads automatically.

1. **Never write a number into a results file, the README or the paper that was not
   produced by executing code.** No estimates, no plausible values.
2. **Code changes never rewrite a scientific claim.** If a change makes the code disagree
   with the paper, add an entry to `results/DISCREPANCIES.md` and stop.

## If time runs out

Minimum publishable version: compositional arm, one or more models, prompt v2, no human
annotation, §7.5 reported as heuristic with the reachability caveat (three of seven
categories are unreachable by any counterfactual over the logical form). That still contains
the actual contribution — the depth threshold — and it is honest. Ship it rather than
stalling.

## Where to look

| File | For |
|---|---|
| `results/PAPER_DATA.md` | generated numbers, paste-ready |
| `results/SECTION7.md` | what was measured, with every caveat |
| `results/DISCREPANCIES.md` | 18 known code-vs-paper gaps and status |
| `docs/TASKS.md` | the same phases as detail cards |
| `docs/V2_SCOPE.md` | what was cut, and why |
| `docs/CODEBOOK.md` | the annotation instrument |
| `make help` | every target |

Do not read `paper/CriteriaLogic.md` in full (~15k tokens) unless editing it.
