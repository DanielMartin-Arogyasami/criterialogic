# RUN — turnkey commands

Run these verbatim. Results land in `results/` as JSON plus `report.md`.

## 0. Requirements

Python 3.10 or newer, and one runtime dependency: `pydantic>=2,<3`. `pytest` and `ruff`
come with the `[dev]` extra, `openai` with `[llm]`. Nothing else — the statistics layer is
standard-library only by design.

On a corporate or otherwise restricted network, point pip at your organisation's package
index rather than PyPI (`pip install --index-url <your-index> -e ".[dev]"`, or configure
`pip.conf`). The dependency set is small and standard, so an internal mirror will have it.

## 1. Set up and preflight (offline, no API key)

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/preflight.py      # <- run this first
```

`preflight.py` is the answer to "does this installation work". It checks the interpreter,
the dependency, the resolved data directory, the snapshot and atom pool, then runs a real
evaluation through both arms and asserts the diagnostics behave as designed. Every check
prints PASS or FAIL with a fix; the exit code is the number of failures. It needs no
network and no key.

Then the full offline sweep and the test suite:

```bash
python scripts/run_eval.py
pytest -q
ruff check .
```

### Where the data is found

The snapshot and atom pool are committed, and their location is resolved rather than
assumed: `$CRITERIALOGIC_DATA_DIR` if set, else `./data`, else `<repo root>/data` found
from the installed package. So `criterialogic-eval` works from any working directory after
`pip install -e .`. A non-editable `pip install .` does not ship the data — use the
editable install from a clone, or set `CRITERIALOGIC_DATA_DIR`.

## 2. Inspect the data before evaluating anything

```bash
# Arm 1: how many criteria the snapshot yields, the polarity split, the depth histogram.
# These are the numbers Section 3 of the manuscript reports. No network, no key.
python scripts/build_real_criteria.py --stats

# Arm 2: build an item set and check the pool digest.
python scripts/build_logic_set.py --depths 2,3,4,5,6 --n-per-depth 60 --seed 29
```

## 3. Real LLM results

```bash
pip install -e ".[llm]"
export OPENAI_API_KEY=sk-...                 # Windows: setx OPENAI_API_KEY "sk-..."
export CRITERIALOGIC_LLM_MODEL=gpt-4o-mini

# the depth sweep
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model openai
# the realism check
python scripts/run_eval.py --task real_criteria --model openai

# second / third system — same prompt, different host
export OPENROUTER_API_KEY=...    # or TOGETHER_API_KEY
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model openrouter
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model together
```

`--prompt-version 1` reproduces the exact prompts behind the v0.2 reported numbers. It does
**not** reproduce the numbers: the requested temperature was rejected by the model so every
completion used the API default, and the response cache is not redistributed. Items, gold
labels and prompts are deterministic; completions are not. The released per-item
predictions are the record. Renderer v2 is the default and fixes both the currency
rendering defect and the exclusion-polarity prompt ambiguity. See `results/SECTION7.md`.

## 4. Collect the paper's numbers

```bash
python scripts/collect_paper_data.py
```

Writes `results/PAPER_DATA.md` (paste-ready tables formatted to match the manuscript's own
section headings) and `results/paper_data.v2.json` (machine-readable, with provenance). It
recomputes every aggregate from the persisted per-item predictions rather than copying a
stored one, runs the integrity gates as part of collection, and prints a bracket plus the
command that fills it wherever an experiment has not been run.

Then check the manuscript against it:

```bash
python scripts/collect_paper_data.py --verify
```

Exits non-zero with a line per mismatch, so the paper cannot silently drift from the data.
This runs in CI. The main path needs no dependencies at all — the statistics layer is
loaded by file path — so it works on a bare checkout.

## 5. Annotation

```bash
python scripts/annotation_export.py --results results/ --n 200 --out annotation/ \
    --depths 2,3,4,5,6 --n-per-depth 60
# calibration session on 20 items first — discard them, they do not enter the statistics
# then both annotators label independently, from docs/CODEBOOK.md
python scripts/annotation_report.py --a annotation/errors_annotator1.csv \
    --b annotation/errors_annotator2.csv --adjudication-out annotation/adjudication.csv
# fill resolved_category for every disagreement, then:
python scripts/annotation_report.py --a annotation/errors_annotator1.csv \
    --b annotation/errors_annotator2.csv \
    --adjudication annotation/adjudication.csv \
    --automatic annotation/automatic_labels_HELD_BACK.csv \
    --out results/agreement.json
```

## 6. Rebuild the snapshot (only if you mean to)

```bash
python scripts/fetch_ctgov_snapshot.py --offline    # rebuild the pool from the cache
python scripts/fetch_ctgov_snapshot.py --recruiting --limit 300 --first-posted-from 2026-06-01
```

A rebuild changes the atom pool digest and therefore invalidates every reported number.
Read `data/README.md` first.

## 7. Tests and lint

```bash
pytest -q
ruff check .
```
