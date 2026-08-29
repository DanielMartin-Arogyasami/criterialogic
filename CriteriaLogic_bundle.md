### FILE: README.md
`````markdown
# CriteriaLogic
**A public benchmark for LLM reasoning over clinical-trial eligibility criteria.**
LLM patient–trial matching systems often fail on the *logical structure* of
eligibility criteria — nested AND/OR, negation/polarity, temporal windows, and
numeric thresholds — and the field has no shared way to measure this.
CriteriaLogic provides a harmonized benchmark, an open evaluation toolkit, a
public leaderboard, and a seven-category reasoning-failure taxonomy.
> **Data policy:** public/synthetic data only. Chia is CC-BY (releasable);
> ClinicalTrials.gov is public; **n2c2 2018 is DUA-gated and never redistributed**
> — we release the harness + a DUA pointer (see `data/README.md`).
## Quickstart
```bash
git clone https://github.com/USERNAME/criterialogic.git
cd criterialogic
python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -e .
# Runs end-to-end with NO external data (real n2c2 criteria + synthetic patients):
python scripts/run_eval.py
```
This evaluates two baselines (a rule-based logic floor and an illustrative
negation-blind model) on the matching (Task C) and compositional (Task D) tasks,
prints a Markdown report, and writes JSON results to `results/`.
> Note: on the *synthetic* demo set the rule-based baseline evaluates an
> already-structured form and is therefore an oracle (≈ perfect). The demo
> exists to show the **pipeline + diagnostics** working (depth-stratified
> accuracy, calibration, failure taxonomy), not to report benchmark findings.
> Real findings come from the full data + LLM/encoder baselines.
## Tasks
- **A. Structuring** — free-text → LogicalForm (gold: Chia).
- **B. Typing & polarity** — type / inclusion-exclusion / qualifiers (gold: Chia).
- **C. Matching** — met/not-met for (record, criterion) (gold: n2c2 2018).
- **D. Compositional logic** — controlled nested AND/OR/NOT (synthetic from ClinicalTrials.gov).
- **Cross-cutting** — calibration & abstention (ECE, selective accuracy).
## Add your model (leaderboard)
Implement one method:
```python
from criterialogic.models.base import Model
from criterialogic.tasks.base import Item, Prediction
class MyModel(Model):
    name = "my_model"
    def predict(self, item: Item) -> Prediction:
        ...  # return Prediction(item_id=item.item_id, label=<bool>, confidence=<0..1>)
```
Run it, emit a submission JSON, and validate/score with `criterialogic.leaderboard`.
See `CONTRIBUTING.md`.
## Run an LLM baseline (OpenAI)
The compositional task (Task D) is synthetic by design, so you can produce **real** LLM results
for it with no gated data — just an API key.
```bash
pip install -e ".[llm]"
export OPENAI_API_KEY=sk-...
export CRITERIALOGIC_LLM_MODEL=gpt-4o-mini      # optional; any chat model you can access
python scripts/run_eval.py --task compositional --model openai
python scripts/run_eval.py --task matching --model openai      # LLM on synthetic patients
```
Responses are cached under `.criterialogic_cache/` (keyed by model + prompt), so re-runs are free
and interrupted runs resume. Calls use `temperature=0` for reproducibility and fail gracefully
per item (a bad call becomes a low-confidence abstain rather than aborting the run). The default
`python scripts/run_eval.py` sweep stays offline (`rule_based`, `negation_blind`) and needs no key.
To characterise the model's errors with the reasoning-failure taxonomy, export the error set for
annotation and compute agreement (see `criterialogic/taxonomy/reliability.py`):
```python
from criterialogic.taxonomy.reliability import export_error_set, reliability_report
export_error_set(items, predictions, "errors.csv")   # fill the human_category column, then:
print(reliability_report(items, predictions, "errors_annotated.csv"))
```
## Repository layout
See `docs/index.md`. Core: `criterialogic/schema` (the logical form),
`criterialogic/oracle.py` (3-valued evaluator), `tasks/`, `models/`, `metrics/`,
`taxonomy/`, `eval/`, `leaderboard/`.
## Reproducibility
Pinned deps (`pyproject.toml`), fixed seeds, and model identifiers + inference
parameters logged into every result file. The synthetic logic set is regenerable
(`scripts/build_logic_set.py`).
## Citation
See `CITATION.cff`. License: MIT.
`````
### FILE: RUN.md
`````markdown
# RUN — CriteriaLogic (turnkey commands)
Run these verbatim. Nothing here needs code changes. Results land in `results/` (JSON + `report.md`).
## 1. Set up + smoke-test (offline, no API key)
macOS / Linux / WSL:
    bash setup_and_run.sh
Windows (PowerShell):
    python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -e ".[dev]"; python scripts/run_eval.py; pytest -q
## 2. Offline demo only (no key)
    python scripts/run_eval.py
    python scripts/run_eval.py --task compositional --model negation_blind
## 3. Real OpenAI results — Task D needs no gated data
    pip install -e ".[llm]"
    export OPENAI_API_KEY=sk-...              # Windows: setx OPENAI_API_KEY "sk-..."
    export CRITERIALOGIC_LLM_MODEL=gpt-4o-mini
    python scripts/run_eval.py --task compositional --model openai
    python scripts/run_eval.py --task matching --model openai   # synthetic patients
## 4. Tests + lint
    pytest -q
    ruff check .
## 5. Pull datasets (optional)
    python scripts/download_data.py --status
    python scripts/download_data.py --chia
    python scripts/download_data.py --ctgov "type 2 diabetes" --n 100
    # n2c2 is DUA-gated: request at https://n2c2.dbmi.hms.harvard.edu/ , place XML in data/raw/n2c2_2018/
## 6. Bigger compositional set (tighter estimates)
    python scripts/build_logic_set.py --n-per-depth 100 --max-depth 4 --seed 29 --out data/processed/logic_set.json
`````
### FILE: setup_and_run.sh
`````bash
#!/usr/bin/env bash
# Turnkey setup + offline smoke-test for CriteriaLogic. No API key needed.
set -e
echo "[1/4] Create virtual environment (.venv)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
echo "[2/4] Install CriteriaLogic (editable, with dev tools)"
python -m pip install -q --upgrade pip
pip install -q -e ".[dev]"
echo "[3/4] Run the offline demo (real n2c2 criteria + synthetic patients, no external data)"
python scripts/run_eval.py
echo "[4/4] Run the test suite"
pytest -q
echo
echo "OK. Results are in results/. To run a real OpenAI model:"
echo "  source .venv/bin/activate"
echo "  pip install -e \".[llm]\" && export OPENAI_API_KEY=sk-... && python scripts/run_eval.py --task compositional --model openai"
`````
### FILE: unpack.py
`````python
#!/usr/bin/env python3
"""Reconstruct the CriteriaLogic repository from the single-file Markdown bundle.
Usage:
    python unpack.py CriteriaLogic_bundle.md [dest_dir]    # dest_dir defaults to "."
Each file in the bundle is a section of the form:
    ### FILE: <relative/path>
    ````<lang>
    ...verbatim file contents...
    ````
The opening fence is four or more backticks (so any ``` blocks *inside* a file are
preserved verbatim); the matching closing fence is a line of exactly those backticks.
"""
from __future__ import annotations
import pathlib
import re
import sys
_HEADER = re.compile(r"^### FILE:\s*(.+?)\s*$")
_FENCE = re.compile(r"^(`{3,})")
def unpack(bundle_path: str, dest_dir: str = ".") -> int:
    lines = pathlib.Path(bundle_path).read_text(encoding="utf-8").splitlines()
    dest = pathlib.Path(dest_dir)
    i, n, written = 0, len(lines), 0
    while i < n:
        m = _HEADER.match(lines[i])
        if not m:
            i += 1
            continue
        relpath = m.group(1).strip()
        i += 1
        while i < n and not _FENCE.match(lines[i]):  # find opening fence
            i += 1
        if i >= n:
            break
        ticks = _FENCE.match(lines[i]).group(1)
        i += 1
        body: list[str] = []
        while i < n and lines[i].strip() != ticks:  # collect until closing fence
            body.append(lines[i])
            i += 1
        i += 1  # consume closing fence
        out = dest / relpath
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(body) + "\n", encoding="utf-8")
        written += 1
        print(f"wrote {out}")
    print(f"done: reconstructed {written} files into {dest.resolve()}")
    return written
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python unpack.py <bundle.md> [dest_dir]")
        sys.exit(1)
    unpack(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
`````
### FILE: .cursorrules
`````text
CriteriaLogic — public benchmark for LLM reasoning over clinical-trial eligibility criteria.
RUN
- Install: pip install -e .            (Python >=3.10; only runtime dep is pydantic v2)
- Demo (no external data): python scripts/run_eval.py        (or: criterialogic-eval)
- Tests: pytest -q   (23 tests)        Lint: ruff check .
LAYOUT
- criterialogic/schema/logical_form.py  harmonized logical form (pydantic v2) + canonicalize()
- criterialogic/oracle.py               three-valued (Kleene) evaluator = ground truth + rule-based engine
- criterialogic/data/                   n2c2_criteria.py (13 public criteria), synthetic.py (seeded patients),
                                         loaders/{chia,n2c2,ctgov}.py, harmonize.py, splits.py, download.py
- criterialogic/tasks/                  base.py (Item, Prediction, expression_depth) + A–D + calibration
- criterialogic/models/                 base.py (Model interface) + rule_based, naive(negation_blind); encoder/llm_* are stubs
- criterialogic/metrics/                classification, matching, logic, calibration, extraction (all from scratch)
- criterialogic/taxonomy/               7 failure categories + heuristic labeler
- criterialogic/eval/ runner+report     criterialogic/leaderboard/ submit+score     criterialogic/cli.py
HARD CONSTRAINTS
- Public/synthetic data ONLY. NEVER commit data/raw/ (n2c2 2018 is DUA-gated).
- Metrics implemented from scratch — do NOT add sklearn/numpy/pandas. Core stays stdlib + pydantic.
- New models subclass Model and return Prediction(label: bool, confidence in 0..1). New metrics are pure functions.
- Integrity: synthetic/oracle numbers are pipeline checks, NOT empirical findings.
WORKING STYLE (to save tokens)
- Be concise: no preamble/postamble, do not restate the request, prefer prose over bullets.
- Make minimal targeted edits; show only changed lines — never reprint whole unchanged files.
- Reuse existing patterns; don't re-derive run/test commands or re-summarize files already seen in the session.
TURNKEY RUN
- Setup + offline demo + tests: bash setup_and_run.sh
- OpenAI model: pip install -e ".[llm]" && export OPENAI_API_KEY=... && python scripts/run_eval.py --task compositional --model openai
- Full command list: RUN.md. Prefer running scripts over editing code.
`````
### FILE: .cursor/rules/project.mdc
`````markdown
---
description: CriteriaLogic project map, run/test commands, and core constraints
alwaysApply: true
---
CriteriaLogic — a public benchmark for LLM reasoning over clinical-trial eligibility criteria.
Run: `pip install -e .` (Python >=3.10; only runtime dep is pydantic v2). Demo: `python scripts/run_eval.py` (or `criterialogic-eval`). Tests: `pytest -q` (23). Lint: `ruff check .`.
Layout: `schema/logical_form.py` = harmonized logical form (pydantic v2) + `canonicalize()`; `oracle.py` = three-valued Kleene evaluator (ground truth + rule-based engine); `data/` = `n2c2_criteria.py` (13 public criteria), `synthetic.py` (seeded patients), `loaders/{chia,n2c2,ctgov}.py`, `harmonize.py`, `splits.py`, `download.py`; `tasks/` = `base.py` (Item, Prediction, expression_depth) + A–D + calibration; `models/` = `base.py` (Model interface) + `rule_based`, `naive` (negation_blind), with `encoder`/`llm_*` as import-safe stubs; `metrics/` = classification, matching, logic, calibration, extraction (all from scratch); `taxonomy/` = 7 failure categories + heuristic labeler; `eval/` = runner + report; `leaderboard/` = submit + score; `cli.py` backs the console script.
Hard constraints: public/synthetic data ONLY — never commit `data/raw/` (n2c2 is DUA-gated); metrics stay dependency-free (no sklearn/numpy/pandas; core is stdlib + pydantic); new models subclass `Model` and return `Prediction(label: bool, confidence 0..1)`; new metrics are pure functions; synthetic/oracle numbers are pipeline checks, not findings.
Style (save tokens): concise, no preamble/postamble, prose over bullets, minimal targeted edits, show only changed lines, reuse existing patterns, don't re-derive commands or re-summarize seen files.
Turnkey: to set up and run, execute `bash setup_and_run.sh` (offline, no key); full commands in `RUN.md`. Prefer running provided scripts over editing code; do not refactor/explain unless asked.
`````
### FILE: .cursor/rules/run.mdc
`````markdown
---
description: How to set up and run CriteriaLogic with minimal model effort (turnkey command-runner)
alwaysApply: true
---
This project is turnkey — running it needs almost no reasoning. Prefer running the provided
commands/scripts verbatim over reading, rewriting, or explaining code.
Set up + offline smoke-test (no API key), one command:
- macOS/Linux/WSL: `bash setup_and_run.sh`
- Windows: `python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -e ".[dev]"; python scripts/run_eval.py; pytest -q`
Run a real OpenAI model (needs `OPENAI_API_KEY`):
`pip install -e ".[llm]"` then `python scripts/run_eval.py --task compositional --model openai`
The full command list is in `RUN.md`. Tests: `pytest -q`. Lint: `ruff check .`.
Do NOT, unless explicitly asked: refactor, rewrite, reformat, or regenerate code; add dependencies;
explain the codebase; or "improve" files. When asked to run something, run the matching command from
`RUN.md` and report only its output. Keep replies to the command and its result — this keeps token use low.
`````
### FILE: .cursor/rules/data-and-security.mdc
`````markdown
---
description: Data-layer release boundary and security conventions
globs: criterialogic/data/**/*.py,scripts/download_data.py
alwaysApply: false
---
Release boundary: Chia (CC-BY) and ClinicalTrials.gov are fetchable; n2c2 2018 is DUA-gated — never download or commit it; `data/raw/` is gitignored. The downloader is stdlib-only (urllib) — do not add `requests` as a hard dependency.
Keep these security properties when editing data/download code: open only `https://` URLs (reject `file://`/`ftp://`); cap download byte size and a zip's total uncompressed size + file count before `extractall`; if using Hugging Face, pin `revision=` and avoid `trust_remote_code=True`; parse n2c2 XML with `defusedxml` (or treat strictly as trusted DUA input); `random.Random(seed)` is intentional for reproducibility (`# nosec B311`), not a weakness.
`````
### FILE: pyproject.toml
`````toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
[project]
name = "criterialogic"
version = "0.1.0"
description = "A public benchmark for LLM reasoning over clinical-trial eligibility criteria."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "Daniel Martin Arogyasami" }]
keywords = ["clinical trials", "eligibility criteria", "benchmark", "LLM", "logical reasoning", "clinical NLP"]
dependencies = [
    "pydantic>=2,<3",
]
[project.optional-dependencies]
encoder = ["transformers>=4.40", "torch>=2.2"]
llm = ["anthropic>=0.40", "openai>=1.40"]
dev = ["pytest>=8", "ruff>=0.5"]
[project.scripts]
criterialogic-eval = "criterialogic.cli:main"
[project.urls]
Homepage = "https://github.com/USERNAME/criterialogic"
Leaderboard = "https://huggingface.co/spaces/USERNAME/criterialogic-leaderboard"
[tool.setuptools]
packages = ["criterialogic", "criterialogic.schema", "criterialogic.data",
            "criterialogic.data.loaders", "criterialogic.tasks", "criterialogic.models",
            "criterialogic.metrics", "criterialogic.taxonomy", "criterialogic.eval",
            "criterialogic.leaderboard"]
[tool.pytest.ini_options]
testpaths = ["tests"]
[tool.ruff]
line-length = 110
[tool.ruff.lint]
# Stable, version-independent baseline. E501 (line length) is not enforced so that
# example command lines in docstrings stay on one line and copy-pasteable.
select = ["E", "F", "I", "W"]
ignore = ["E501"]
`````
### FILE: .github/workflows/ci.yml
`````yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest -q
      - run: python scripts/run_eval.py   # end-to-end smoke test (no external data)
`````
### FILE: .gitignore
`````text
# Data-release boundary: raw data is NEVER committed (esp. DUA-gated n2c2).
data/raw/
data/processed/
results/
*.pyc
__pycache__/
*.egg-info/
.venv/
.pytest_cache/
.ruff_cache/
.criterialogic_cache/
`````
### FILE: CITATION.cff
`````yaml
cff-version: 1.2.0
title: "CriteriaLogic: A Public Benchmark for Logical Reasoning over Clinical-Trial Eligibility Criteria"
message: "If you use this benchmark, please cite it."
type: software
authors:
  - family-names: "Arogyasami"
    given-names: "Daniel Martin"
version: 0.1.0
date-released: "2026-06-10"
license: MIT
repository-code: "https://github.com/USERNAME/criterialogic"
keywords:
  - clinical trial eligibility
  - patient-trial matching
  - benchmark
  - large language models
  - logical reasoning
  - clinical NLP
`````
### FILE: CONTRIBUTING.md
`````markdown
# Contributing / Leaderboard submissions
## Submit a model
1. Subclass `criterialogic.models.base.Model` and implement `predict(item) -> Prediction`.
2. Run it over the held-out items for a task and write a submission file:
   `{"model": "<name>", "task": "<task>", "predictions": [{"item_id","label","confidence"}, ...]}`.
3. Validate and score:
   ```python
   from criterialogic.leaderboard.submit import load_submission, validate_against_items
   from criterialogic.leaderboard.score import score_submission
   sub = load_submission("submission.json")
   validate_against_items(sub, items)
   print(score_submission(sub, items)["metrics"])
   ```
4. Open a PR adding your result JSON under `results/leaderboard/`.
## Code
- `pip install -e ".[dev]"`, then `pytest` and `ruff check .` before a PR.
- Public/synthetic data only. Never commit anything under `data/raw/`.
`````
### FILE: DATASHEET.md
`````markdown
# Datasheet for CriteriaLogic (Datasheet for Datasets, Gebru et al., 2021)
## Motivation
CriteriaLogic was created to measure whether NLP/LLM systems reason correctly over
the **logical structure** of clinical-trial eligibility criteria (nested AND/OR,
negation/polarity, temporal windows, numeric thresholds), which existing,
heterogeneous evaluations cannot compare across systems.
## Composition
- **Chia** (Kury et al., 2020): 1,000 Phase-IV trials; 12,409 annotated criteria,
  41,487 entities (15 types), 25,017 relations (12 types). CC-BY 4.0; releasable.
- **n2c2 2018 Track 1** (Stubbs et al., 2019): 288 longitudinal records, 13 criteria,
  binary met/not-met. **DUA-gated; not redistributed** — definitions are public and
  encoded in code; records require the Harvard DBMI DUA.
- **Compositional stress-test**: synthetic, generated deterministically from
  ClinicalTrials.gov criteria with a fixed seed; regenerable (`build_logic_set.py`).
## Collection
Chia and n2c2 are pre-existing, expert-annotated gold resources. The synthetic set
is machine-generated from public criteria; no human subjects are recruited and no
new patient data is collected.
## Preprocessing / harmonization
All sources map onto one logical-form schema (`schema/logical_form.py`). Mapping is
documented and validated (`schema/validators.py`). Numeric and temporal qualifiers
are captured as typed constraints.
## Uses
Research benchmark for eligibility-logic reasoning. **Not** a medical device; makes
no patient-care claims. Intended for offline model evaluation and error analysis.
## Distribution
Chia-derived artifacts + the toolkit are released under MIT/CC-BY on GitHub and
Hugging Face. n2c2 components are reproducible via the DUA pointer only.
## Maintenance
Versioned via `SCHEMA_VERSION` and package version; issues/PRs on GitHub.
`````
### FILE: LICENSE
`````text
MIT License
Copyright (c) 2026 Daniel Martin Arogyasami
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
`````
### FILE: criterialogic/__init__.py
`````python
"""CriteriaLogic — a public benchmark for LLM reasoning over clinical-trial
eligibility criteria. Public/synthetic data only.
"""
from criterialogic.schema.logical_form import SCHEMA_VERSION, LogicalForm  # noqa: F401
__version__ = "0.1.0"
`````
### FILE: criterialogic/cli.py
`````python
"""Command-line entrypoint for CriteriaLogic.
Exposed as the ``criterialogic-eval`` console script (see pyproject) and reused by
``scripts/run_eval.py``. Living inside the installed package is what makes the
console command importable after ``pip install`` (a bare ``scripts/`` directory is
not installed, so an entry point pointing at it fails).
Zero-argument demo (runs end-to-end with NO external data):
    criterialogic-eval
    # or, equivalently, from a clone:  python scripts/run_eval.py
Targeted run:
    criterialogic-eval --task matching --model rule_based
    criterialogic-eval --task compositional --model negation_blind
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.eval.report import render_report
from criterialogic.eval.runner import run_task
from criterialogic.models import OFFLINE_MODELS, REGISTRY
from criterialogic.tasks.compositional import generate_compositional_items
def build_items(task: str):
    if task == "matching":
        return generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=8, seed=13)
    if task == "compositional":
        return generate_compositional_items(n_per_depth=12, max_depth=3, seed=29)
    raise SystemExit(f"Unknown/unsupported demo task: {task}")
def main() -> None:
    ap = argparse.ArgumentParser(description="Run a CriteriaLogic evaluation.")
    ap.add_argument("--task", choices=["matching", "compositional"], default=None)
    ap.add_argument("--model", choices=sorted(REGISTRY), default=None)
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()
    tasks = [args.task] if args.task else ["matching", "compositional"]
    models = [args.model] if args.model else OFFLINE_MODELS
    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    results = []
    for task in tasks:
        items = build_items(task)
        for mname in models:
            model = REGISTRY[mname]()
            res = run_task(model, items, seed=13)
            results.append(res)
            out = Path(args.outdir) / f"{task}__{mname}.json"
            out.write_text(json.dumps(res, indent=2))
            print(f"[wrote] {out}")
    report = render_report(results)
    (Path(args.outdir) / "report.md").write_text(report)
    print("\n" + report)
if __name__ == "__main__":
    main()
`````
### FILE: criterialogic/data/__init__.py
`````python
"""Data subpackage: source loaders, harmonization, splits, and synthetic generation."""
`````
### FILE: criterialogic/data/download.py
`````python
"""Data acquisition for CriteriaLogic — fetch the releasable sources, point to the gated one.
Release boundary, enforced in code:
  * **Chia** (CC-BY 4.0)            → downloaded from figshare as raw brat .txt/.ann.
  * **ClinicalTrials.gov** (public) → cached from the public API v2 (no download needed at run time).
  * **n2c2 2018** (DUA-gated)       → **never downloaded**; we only report local status and the portal URL.
Dependency posture: standard library only (``urllib``), so ``pip install criterialogic`` is
sufficient. An optional Hugging Face route (``download_chia_hf``) additionally needs ``datasets``.
The functions here are importable and unit-testable; ``scripts/download_data.py`` is a thin CLI
over them (mirroring how ``criterialogic.cli`` backs ``scripts/run_eval.py``).
"""
from __future__ import annotations
import hashlib
import json
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
# ---- Source coordinates (verifiable, public) ------------------------------- #
FIGSHARE_API = "https://api.figshare.com/v2/articles"
CHIA_FIGSHARE_ARTICLE = 11855817  # "Chia Annotated Datasets" (DOI 10.6084/m9.figshare.11855817)
CHIA_HF_DATASET = "bigbio/chia"
N2C2_PORTAL = "https://n2c2.dbmi.hms.harvard.edu/"
DEFAULT_DATA_ROOT = Path("data/raw")
_USER_AGENT = "CriteriaLogic-downloader/0.1 (+https://github.com/USERNAME/criterialogic)"
class DownloadError(RuntimeError):
    """Raised when a releasable source cannot be retrieved."""
# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #
def _http_json(url: str, timeout: int = 60) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.URLError as e:  # pragma: no cover - network dependent
        raise DownloadError(
            f"Could not reach {url} ({e}). If you are behind a restricted network, run this in your "
            f"own environment or ask an administrator to allow the domain."
        ) from e
def _download_file(url: str, dest: Path, expected_md5: str | None = None, timeout: int = 300) -> Path:
    """Stream a URL to ``dest`` (atomic), optionally verifying an MD5 checksum."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    md5 = hashlib.md5()
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as fh:
            for chunk in iter(lambda: resp.read(1 << 20), b""):
                fh.write(chunk)
                md5.update(chunk)
    except urllib.error.URLError as e:  # pragma: no cover - network dependent
        raise DownloadError(f"Failed to download {url} ({e}).") from e
    if expected_md5 and md5.hexdigest() != expected_md5:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"Checksum mismatch for {url}: got {md5.hexdigest()}, expected {expected_md5}.")
    tmp.replace(dest)
    return dest
def _extract_archives(archives: list[Path], dest: Path) -> int:
    """Extract every .zip in ``archives`` into ``dest``. Returns the count of .ann files found after."""
    dest.mkdir(parents=True, exist_ok=True)
    for arc in archives:
        if arc.suffix.lower() == ".zip":
            with zipfile.ZipFile(arc) as zf:
                zf.extractall(dest)
    return sum(1 for _ in dest.rglob("*.ann"))
# --------------------------------------------------------------------------- #
# Chia (releasable)
# --------------------------------------------------------------------------- #
def download_chia_figshare(dest: Path | str = DEFAULT_DATA_ROOT / "chia", force: bool = False) -> dict:
    """Download + extract the Chia brat corpus from figshare into ``dest``.
    Idempotent: if ``dest`` already contains .ann files and ``force`` is False, it is a no-op.
    Returns a small summary dict (files downloaded, .ann count, destination).
    """
    dest = Path(dest)
    existing = sum(1 for _ in dest.rglob("*.ann"))
    if existing and not force:
        return {"status": "already_present", "ann_files": existing, "dest": str(dest)}
    meta = _http_json(f"{FIGSHARE_API}/{CHIA_FIGSHARE_ARTICLE}")
    files = meta.get("files", []) if isinstance(meta, dict) else []
    if not files:
        raise DownloadError(f"figshare article {CHIA_FIGSHARE_ARTICLE} returned no files.")
    with tempfile.TemporaryDirectory() as td:
        downloaded: list[Path] = []
        for f in files:
            url = f.get("download_url")
            name = f.get("name", "chia_file")
            if not url:
                continue
            local = _download_file(url, Path(td) / name, expected_md5=f.get("computed_md5"))
            downloaded.append(local)
        n_ann = _extract_archives(downloaded, dest)
        # also copy any loose (non-zip) .txt/.ann that came straight from figshare
        for f in downloaded:
            if f.suffix.lower() in {".ann", ".txt"}:
                shutil.copy2(f, dest / f.name)
        n_ann = sum(1 for _ in dest.rglob("*.ann"))
    if n_ann == 0:
        raise DownloadError(
            f"Downloaded {len(downloaded)} figshare file(s) but found no .ann files under {dest}. "
            f"Inspect the archive layout; Chia ships brat .txt/.ann pairs."
        )
    return {"status": "downloaded", "files": len(downloaded), "ann_files": n_ann, "dest": str(dest)}
def download_chia_hf(dest: Path | str = DEFAULT_DATA_ROOT / "chia_hf") -> dict:
    """Alternative Chia route via Hugging Face (`bigbio/chia`). Requires the `datasets` package.
    Note: this yields pre-parsed records, NOT raw brat .txt/.ann, so it does not feed
    `loaders.chia.load_chia_dir` directly; use the figshare route for the brat parser.
    """
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as e:
        raise DownloadError(
            "The Hugging Face route needs `datasets` (pip install datasets). "
            "For the brat .txt/.ann the toolkit parses, prefer download_chia_figshare()."
        ) from e
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    ds = load_dataset(CHIA_HF_DATASET, trust_remote_code=True)  # pragma: no cover - heavy/optional
    out = dest / "chia_hf.jsonl"
    with open(out, "w") as fh:
        for split in ds:  # type: ignore
            for row in ds[split]:  # type: ignore
                fh.write(json.dumps(row, default=str) + "\n")
    return {"status": "downloaded_hf", "dest": str(out)}
# --------------------------------------------------------------------------- #
# ClinicalTrials.gov (public) — cache eligibility text for the Task-D atom pool
# --------------------------------------------------------------------------- #
def cache_ctgov_criteria(
    query: str = "type 2 diabetes",
    n: int = 50,
    dest: Path | str = DEFAULT_DATA_ROOT / "ctgov",
    filename: str | None = None,
) -> dict:
    """Fetch eligibility text for ``n`` trials matching ``query`` and cache as JSON."""
    from criterialogic.data.loaders import ctgov
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    nct_ids = [x for x in ctgov.search_trials(query, page_size=n) if x]
    criteria = ctgov.fetch_eligibility(nct_ids)
    safe = filename or ("ctgov_" + "".join(c if c.isalnum() else "_" for c in query)[:40] + ".json")
    out = dest / safe
    out.write_text(json.dumps(criteria, indent=2))
    return {"status": "cached", "query": query, "n_trials": len(criteria), "path": str(out)}
# --------------------------------------------------------------------------- #
# n2c2 (DUA-gated) — status only, never downloaded
# --------------------------------------------------------------------------- #
def n2c2_status(dest: Path | str = DEFAULT_DATA_ROOT / "n2c2_2018") -> dict:
    """Report whether DUA-obtained n2c2 XML files are present locally. Never downloads."""
    dest = Path(dest)
    files = sorted(dest.glob("*.xml")) if dest.exists() else []
    return {
        "present": bool(files),
        "n_files": len(files),
        "dest": str(dest),
        "portal": N2C2_PORTAL,
        "note": "n2c2 is DUA-gated and never downloaded/committed; obtain via the portal and place XML here.",
    }
def verify(data_root: Path | str = DEFAULT_DATA_ROOT) -> dict:
    """Summarize what is present locally across all sources."""
    root = Path(data_root)
    chia_ann = sum(1 for _ in (root / "chia").rglob("*.ann")) if (root / "chia").exists() else 0
    ctgov_files = len(list((root / "ctgov").glob("*.json"))) if (root / "ctgov").exists() else 0
    return {
        "chia_ann_files": chia_ann,
        "ctgov_cached_queries": ctgov_files,
        "n2c2": n2c2_status(root / "n2c2_2018"),
    }
`````
### FILE: criterialogic/data/harmonize.py
`````python
"""Map each source onto the harmonized schema (one entrypoint per source).
- n2c2 criteria  -> `data.n2c2_criteria.n2c2_criteria_as_logical_forms()` (public).
- Chia           -> `data.loaders.chia.load_chia_dir(...)`.
- ClinicalTrials.gov text -> parsed downstream (Task A model) or used to seed Task D.
This module is the seam where the documented source->schema mapping lives.
"""
from __future__ import annotations
from criterialogic.data.n2c2_criteria import n2c2_criteria_as_logical_forms
from criterialogic.schema.validators import validate_corpus
def harmonized_n2c2_criteria():
    forms = n2c2_criteria_as_logical_forms()
    validate_corpus(forms)
    return forms
`````
### FILE: criterialogic/data/loaders/__init__.py
`````python
"""Source loaders: Chia (releasable), n2c2 2018 (DUA-gated), ClinicalTrials.gov (public)."""
`````
### FILE: criterialogic/data/loaders/chia.py
`````python
"""Load + parse the Chia corpus (brat standoff) into LogicalForm records.
Chia ships as brat .txt/.ann pairs: T-lines are entities (type + span + text),
R-lines are typed relations including the AND/OR connectors and Has_negation /
Has_value / Has_temporal. Chia is CC-BY and fully releasable.
This is a first-pass mapper for the common patterns; the DAG->tree assembly for
deeply nested criteria and a few rarer relation types are marked TODO. Download
Chia via `scripts/download_data.py` (figshare / Hugging Face `bigbio/chia`).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from criterialogic.schema.logical_form import (
    Atom,
    Entity,
    EntityType,
    Expression,
    LogicalForm,
    Not,
    Polarity,
    Source,
)
# Chia entity type -> our coarse EntityType
_TYPE_MAP = {
    "Condition": EntityType.CONDITION,
    "Drug": EntityType.DRUG,
    "Procedure": EntityType.PROCEDURE,
    "Measurement": EntityType.MEASUREMENT,
    "Observation": EntityType.OBSERVATION,
    "Person": EntityType.PERSON,
    "Device": EntityType.DEVICE,
    "Visit": EntityType.VISIT,
    "Mood": EntityType.OTHER,
    "Value": EntityType.OTHER,
    "Temporal": EntityType.OTHER,
    "Negation": EntityType.OTHER,
    "Qualifier": EntityType.OTHER,
}
@dataclass
class _BratEntity:
    tid: str
    etype: str
    text: str
@dataclass
class _BratDoc:
    entities: dict[str, _BratEntity] = field(default_factory=dict)
    relations: list[tuple[str, str, str]] = field(default_factory=list)  # (type, argA, argB)
def parse_ann(ann_text: str) -> _BratDoc:
    doc = _BratDoc()
    for line in ann_text.splitlines():
        if line.startswith("T"):
            m = re.match(r"(T\d+)\t(\S+)[^\t]*\t(.*)", line)
            if m:
                tid, etype = m.group(1), m.group(2)
                doc.entities[tid] = _BratEntity(tid, etype, m.group(3))
        elif line.startswith("R"):
            m = re.match(r"R\d+\t(\S+) Arg1:(\S+) Arg2:(\S+)", line)
            if m:
                doc.relations.append((m.group(1), m.group(2), m.group(3)))
    return doc
def _to_atom(ent: _BratEntity) -> Atom:
    return Atom(entity=Entity(text=ent.text, type=_TYPE_MAP.get(ent.etype, EntityType.OTHER)))
def doc_to_logical_forms(doc: _BratDoc, trial_id: str) -> list[LogicalForm]:
    """First-pass assembly: negation wraps its target; AND/OR connectors group entities.
    TODO: full DAG->tree reduction for multi-level nesting; Has_value/Has_temporal
    attachment onto Atom constraints (requires parsing Value/Temporal entity text).
    """
    negated = {b for (t, a, b) in doc.relations if t.lower().startswith("has_neg")}
    forms: list[LogicalForm] = []
    idx = 0
    for tid, ent in doc.entities.items():
        if ent.etype in {"Value", "Temporal", "Negation", "Qualifier", "Mood"}:
            continue
        expr: Expression = _to_atom(ent)
        if tid in negated:
            expr = Not(operand=expr)
        forms.append(LogicalForm(
            criterion_id=f"chia:{trial_id}:{idx}",
            source=Source.CHIA,
            polarity=Polarity.INCLUSION,  # TODO: inclusion/exclusion from the source file section
            text=ent.text,
            expression=expr,
            metadata={"trial_id": trial_id, "chia_tid": tid},
        ))
        idx += 1
    return forms
def load_chia_dir(root: str) -> list[LogicalForm]:
    """Load every .ann under `root`, pairing with .txt, into LogicalForm records."""
    forms: list[LogicalForm] = []
    for ann in sorted(Path(root).rglob("*.ann")):  # recursive: figshare extracts into subfolders
        doc = parse_ann(ann.read_text(encoding="utf-8", errors="ignore"))
        forms.extend(doc_to_logical_forms(doc, trial_id=ann.stem))
    return forms
`````
### FILE: criterialogic/data/loaders/ctgov.py
`````python
"""Load eligibility text from the public ClinicalTrials.gov API v2.
This is the source for the compositional stress-test pool and for additional
criteria. It is fully public (no DUA). Network access required at runtime.
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request
API = "https://clinicaltrials.gov/api/v2/studies"
def fetch_eligibility(nct_ids: list[str]) -> dict[str, str]:
    """Return {nct_id: eligibility_criteria_text} for the given trials."""
    out: dict[str, str] = {}
    for nct in nct_ids:
        url = f"{API}/{urllib.parse.quote(nct)}?fields=EligibilityCriteria"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
        crit = (
            data.get("protocolSection", {})
            .get("eligibilityModule", {})
            .get("eligibilityCriteria", "")
        )
        out[nct] = crit
    return out
def search_trials(query: str, page_size: int = 20) -> list[str]:
    """Return a list of NCT ids for a query (e.g. condition term)."""
    params = urllib.parse.urlencode({"query.term": query, "pageSize": page_size, "fields": "NCTId"})
    with urllib.request.urlopen(f"{API}?{params}", timeout=30) as resp:
        data = json.load(resp)
    return [
        s.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
        for s in data.get("studies", [])
    ]
`````
### FILE: criterialogic/data/loaders/n2c2.py
`````python
"""Load n2c2 2018 Track-1 records (DUA-gated) and align them to the criteria.
n2c2 is **not redistributable**. Obtain it under the Harvard DBMI DUA (see
`data/README.md`); place the XML files under `data/raw/n2c2_2018/`. This loader
reads the per-patient <TAGS> (met/not-met for each of the 13 criteria) and the
note text. The criterion *definitions* live in `data.n2c2_criteria` (public).
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from criterialogic.data.n2c2_criteria import N2C2_TAGS
_MET_VALUES = {"met", "yes", "true", "1"}
class N2C2NotAvailable(FileNotFoundError):
    pass
def load_patient_labels(xml_path: str) -> dict[str, bool]:
    """Return {criterion_tag: met?} for one patient XML file."""
    tree = ET.parse(xml_path)
    tags_el = tree.getroot().find("TAGS")
    if tags_el is None:
        raise ValueError(f"No <TAGS> element in {xml_path}")
    labels: dict[str, bool] = {}
    for tag in N2C2_TAGS:
        el = tags_el.find(tag)
        if el is not None:
            labels[tag] = (el.get("met", "").strip().lower() in _MET_VALUES)
    return labels
def load_n2c2_dir(root: str = "data/raw/n2c2_2018") -> dict[str, dict[str, bool]]:
    """Return {record_id: {tag: met?}} for all patient files. Raises if DUA data absent."""
    p = Path(root)
    files = sorted(p.glob("*.xml"))
    if not files:
        raise N2C2NotAvailable(
            f"No n2c2 XML found under {root}. n2c2 is DUA-gated and never committed; "
            f"obtain it via the Harvard DBMI portal and see data/README.md."
        )
    return {f.stem: load_patient_labels(str(f)) for f in files}
`````
### FILE: criterialogic/data/n2c2_criteria.py
`````python
"""The 13 n2c2 2018 Track-1 selection criteria, encoded as harmonized LogicalForms.
The criterion *definitions* are public (from the shared-task description, Stubbs
et al., JAMIA 2019); only the patient records are DUA-gated. Encoding them here
(a) demonstrates the n2c2 -> schema mapping concretely and (b) provides real
criteria for the runnable demo, paired with synthetic patient facts.
KNOWN MODELING NOTE — cardinality:
  ADVANCED-CAD is "two or more of {N indicators}". The schema's connectives are
  AND/OR/NOT only (no native k-of-n), so it is expanded to disjunctive normal
  form (an OR over all 2-subsets). This is exact but verbose; a `Cardinality`
  node is a candidate v2 extension. See TRADEOFFS in the paper.
"""
from __future__ import annotations
from itertools import combinations
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Entity,
    EntityType,
    Expression,
    LogicalForm,
    NumericConstraint,
    Polarity,
    Source,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
)
def _cond(text: str) -> Atom:
    return Atom(entity=Entity(text=text, type=EntityType.CONDITION))
def _at_least_k_of(atoms: list[Expression], k: int) -> Expression:
    """Express 'at least k of these' as DNF: OR over all k-subset ANDs."""
    clauses = [BooleanGroup(operator=BoolOp.AND, operands=list(c)) for c in combinations(atoms, k)]
    return BooleanGroup(operator=BoolOp.OR, operands=clauses)
def n2c2_criteria_as_logical_forms() -> list[LogicalForm]:
    """Return all 13 criteria as LogicalForm records (source = n2c2_2018)."""
    def lf(tag: str, text: str, polarity: Polarity, expr: Expression) -> LogicalForm:
        return LogicalForm(
            criterion_id=f"n2c2:{tag}",
            source=Source.N2C2_2018,
            polarity=polarity,
            text=text,
            expression=expr,
            metadata={"tag": tag},
        )
    forms: list[LogicalForm] = []
    forms.append(lf(
        "ABDOMINAL",
        "History of intra-abdominal surgery, small or large intestine resection, or small bowel obstruction.",
        Polarity.INCLUSION,
        BooleanGroup(operator=BoolOp.OR, operands=[
            _cond("intra-abdominal surgery"),
            _cond("intestine resection"),
            _cond("small bowel obstruction"),
        ]),
    ))
    # ADVANCED-CAD: >= 2 of {>=2 CAD meds, history of MI, current angina, ischemia}
    cad_indicators: list[Expression] = [
        Atom(entity=Entity(text="cad medication count", type=EntityType.MEASUREMENT),
             numeric=NumericConstraint(operator=Comparator.GE, value=2, unit="count")),
        Atom(entity=Entity(text="myocardial infarction", type=EntityType.CONDITION),
             temporal=TemporalConstraint(operator=TemporalOp.ANY_HISTORY)),
        Atom(entity=Entity(text="angina", type=EntityType.CONDITION),
             temporal=TemporalConstraint(operator=TemporalOp.CURRENT)),
        _cond("ischemia"),
    ]
    forms.append(lf(
        "ADVANCED-CAD",
        "Advanced cardiovascular disease: two or more of (>=2 CAD medications; history of MI; "
        "current angina; ischemia).",
        Polarity.INCLUSION,
        _at_least_k_of(cad_indicators, 2),
    ))
    forms.append(lf(
        "ALCOHOL-ABUSE",
        "Current alcohol use over the weekly recommended limit.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="alcohol abuse", type=EntityType.LIFESTYLE),
             temporal=TemporalConstraint(operator=TemporalOp.CURRENT)),
    ))
    forms.append(lf(
        "ASP-FOR-MI",
        "Use of aspirin to prevent myocardial infarction.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="aspirin for mi prophylaxis", type=EntityType.DRUG),
             temporal=TemporalConstraint(operator=TemporalOp.CURRENT)),
    ))
    forms.append(lf(
        "CREATININE",
        "Serum creatinine above the upper limit of normal.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="serum creatinine", type=EntityType.MEASUREMENT,
                           codes={"note": "ULN is lab-specific; 1.3 mg/dL used for synthetic eval"}),
             numeric=NumericConstraint(operator=Comparator.GT, value=1.3, unit="mg/dL")),
    ))
    forms.append(lf(
        "DIETSUPP-2MOS",
        "Taken a dietary supplement (excluding vitamin D) in the past 2 months.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="dietary supplement excluding vitamin d", type=EntityType.DRUG),
             temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=2, unit=TimeUnit.MONTHS)),
    ))
    forms.append(lf(
        "DRUG-ABUSE",
        "Drug abuse, current or past.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="drug abuse", type=EntityType.LIFESTYLE),
             temporal=TemporalConstraint(operator=TemporalOp.ANY_HISTORY)),
    ))
    forms.append(lf(
        "ENGLISH",
        "Patient must speak English.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="speaks english", type=EntityType.OBSERVATION)),
    ))
    forms.append(lf(
        "HBA1C",
        "Any HbA1c value between 6.5% and 9.5%.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="HbA1c", type=EntityType.MEASUREMENT),
             numeric=NumericConstraint(operator=Comparator.BETWEEN, value=6.5, upper=9.5, unit="%")),
    ))
    forms.append(lf(
        "KETO-1YR",
        "Diagnosis of ketoacidosis within the past year.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="ketoacidosis", type=EntityType.CONDITION),
             temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=1, unit=TimeUnit.YEARS)),
    ))
    forms.append(lf(
        "MAJOR-DIABETES",
        "Major diabetes-related complication (amputation, nephropathy, retinopathy, or neuropathy).",
        Polarity.INCLUSION,
        BooleanGroup(operator=BoolOp.OR, operands=[
            _cond("amputation"),
            _cond("diabetic nephropathy"),
            _cond("diabetic retinopathy"),
            _cond("diabetic neuropathy"),
        ]),
    ))
    forms.append(lf(
        "MAKES-DECISIONS",
        "Patient must make their own medical decisions.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="makes own medical decisions", type=EntityType.OBSERVATION)),
    ))
    forms.append(lf(
        "MI-6MOS",
        "Myocardial infarction in the past 6 months.",
        Polarity.INCLUSION,
        Atom(entity=Entity(text="myocardial infarction", type=EntityType.CONDITION),
             temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=6, unit=TimeUnit.MONTHS)),
    ))
    return forms
# Convenience: the canonical tag list, in the official order.
N2C2_TAGS = [
    "ABDOMINAL", "ADVANCED-CAD", "ALCOHOL-ABUSE", "ASP-FOR-MI", "CREATININE",
    "DIETSUPP-2MOS", "DRUG-ABUSE", "ENGLISH", "HBA1C", "KETO-1YR",
    "MAJOR-DIABETES", "MAKES-DECISIONS", "MI-6MOS",
]
`````
### FILE: criterialogic/data/splits.py
`````python
"""Deterministic train/test splitting with a leakage check.
Splits are seeded (reproducible). For Chia-derived data, splitting is keyed on
trial id so no trial straddles the train/test boundary (prevents contamination).
"""
from __future__ import annotations
import random
from criterialogic.schema.logical_form import LogicalForm
from criterialogic.schema.validators import check_no_trial_leakage
def split_by_trial(forms: list[LogicalForm], test_frac: float = 0.2, seed: int = 7,
                   key: str = "trial_id") -> tuple[list[LogicalForm], list[LogicalForm]]:
    """Group by trial id, assign whole trials to splits, then verify no leakage."""
    rng = random.Random(seed)
    trials = sorted({f.metadata.get(key, f.criterion_id) for f in forms})
    rng.shuffle(trials)
    n_test = max(1, int(len(trials) * test_frac))
    test_trials = set(trials[:n_test])
    train = [f for f in forms if f.metadata.get(key, f.criterion_id) not in test_trials]
    test = [f for f in forms if f.metadata.get(key, f.criterion_id) in test_trials]
    check_no_trial_leakage(train, test, key=key)
    return train, test
`````
### FILE: criterialogic/data/synthetic.py
`````python
"""Deterministic synthetic patient-fact generation for the runnable demo.
Real criteria (n2c2) + synthetic patients let the full pipeline run with **no
external data**. Generation is seeded and regenerable — never a black box.
Facts are sampled so that each criterion gets a mix of met / not-met / unknown
cases, and the gold label is computed by the oracle (`criterialogic.oracle`).
"""
from __future__ import annotations
import random
from criterialogic.oracle import Fact, PatientFacts, is_met
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    Comparator,
    Expression,
    LogicalForm,
    Not,
)
def _collect_atoms(expr: Expression) -> list[Atom]:
    if isinstance(expr, Atom):
        return [expr]
    if isinstance(expr, Not):
        return _collect_atoms(expr.operand)
    if isinstance(expr, BooleanGroup):
        out: list[Atom] = []
        for op in expr.operands:
            out.extend(_collect_atoms(op))
        return out
    raise TypeError(type(expr))
def _sample_fact_for_atom(atom: Atom, rng: random.Random) -> Fact | None:
    """Produce a plausible fact (or None = absent) that sometimes satisfies the atom."""
    if rng.random() < 0.2:
        return None  # entity simply absent from the record
    present = rng.random() < 0.8
    fact = Fact(present=present)
    if atom.numeric is not None:
        c = atom.numeric
        # center the sample near the threshold so both sides occur
        if c.operator is Comparator.BETWEEN:
            center = (c.value + (c.upper or c.value)) / 2.0
            fact.value = round(rng.uniform(center - 3, center + 3), 2)
        else:
            fact.value = round(c.value + rng.uniform(-2.5, 2.5), 2)
    if atom.temporal is not None:
        op = atom.temporal.operator.value
        if op == "current":
            fact.current = rng.random() < 0.5
            fact.present = fact.present or fact.current
        elif op == "any_history":
            pass
        else:  # windowed: sample a recency on both sides of the window
            base_days = (atom.temporal.value or 1) * 30.4375
            fact.days_ago = round(rng.uniform(0.2 * base_days, 2.2 * base_days), 1)
    return fact
def make_patient_for_criterion(form: LogicalForm, record_id: str, rng: random.Random) -> PatientFacts:
    facts: dict[str, Fact] = {}
    for atom in _collect_atoms(form.expression):
        f = _sample_fact_for_atom(atom, rng)
        if f is not None:
            facts[atom.entity.text] = f
    return PatientFacts(record_id=record_id, facts=facts)
def generate_matching_items(
    forms: list[LogicalForm], n_per_criterion: int = 8, seed: int = 13
):
    """Build Task-C items: each criterion paired with `n_per_criterion` synthetic patients."""
    from criterialogic.tasks.base import Item  # local import to avoid a cycle
    rng = random.Random(seed)
    items: list[Item] = []
    for form in forms:
        tag = form.metadata.get("tag", form.criterion_id)
        for i in range(n_per_criterion):
            rid = f"{tag}-P{i:03d}"
            facts = make_patient_for_criterion(form, rid, rng)
            items.append(Item(
                item_id=f"match:{tag}:{i:03d}",
                task="matching",
                criterion=form,
                facts=facts,
                gold=is_met(form, facts),
                group=tag,
            ))
    return items
`````
### FILE: criterialogic/eval/__init__.py
`````python
"""Evaluation orchestration: a runner that ties model -> task -> metrics, and a reporter."""
`````
### FILE: criterialogic/eval/report.py
`````python
"""Render result dicts (from eval.runner) into a compact Markdown report."""
from __future__ import annotations
def _fmt(x, nd=3):
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x)
def render_report(results: list[dict]) -> str:
    lines: list[str] = ["# CriteriaLogic — evaluation report", ""]
    for r in results:
        m = r["metrics"]
        name = r["model"].get("name", "model")
        lines.append(f"## Task: {r['task']}  ·  Model: {name}  ·  n={r['n_items']}")
        if r["task"] == "matching":
            lines.append(f"- Overall micro-F1: **{_fmt(m['overall_micro_f1'])}**  ·  "
                         f"macro-F1: **{_fmt(m['overall_macro_f1'])}**")
            lines.append("- Per-criterion micro-F1:")
            for tag, v in m["per_criterion"].items():
                lines.append(f"    - {tag}: {_fmt(v['micro_f1'])}  (n={v['n']})")
        elif r["task"] == "compositional":
            lines.append(f"- Overall accuracy: **{_fmt(m['overall_accuracy'])}**")
            lines.append("- Accuracy by nesting depth:")
            for d, v in m["by_depth"].items():
                lines.append(f"    - depth {d}: {_fmt(v['accuracy'])}  (n={v['n']})")
        else:
            lines.append(f"- Accuracy: **{_fmt(m.get('accuracy'))}**")
        lines.append(f"- ECE: {_fmt(r['calibration']['ece'])}  ·  "
                     f"selective-acc @50% coverage: {_fmt(r['calibration'].get('selective_accuracy_at_50pct_coverage'))}")
        if r["failure_taxonomy"]:
            fb = "  ".join(f"{k}={v}" for k, v in sorted(r["failure_taxonomy"].items()))
            lines.append(f"- Failure taxonomy (errors): {fb}")
        else:
            lines.append("- Failure taxonomy (errors): none")
        lines.append("")
    return "\n".join(lines)
`````
### FILE: criterialogic/eval/runner.py
`````python
"""Orchestrates a full evaluation: run a model over a task's items, compute metrics,
attach the failure-taxonomy breakdown and reproducibility metadata.
"""
from __future__ import annotations
import platform
import sys
from datetime import datetime, timezone
from criterialogic.metrics.calibration import expected_calibration_error, selective_accuracy_curve
from criterialogic.metrics.logic import accuracy_by_depth
from criterialogic.metrics.matching import matching_scores
from criterialogic.taxonomy.annotate import failure_breakdown
def run_task(model, items, seed: int | None = None) -> dict:
    """Evaluate `model` on `items` (one task). Returns a result dict ready to serialise."""
    if not items:
        raise ValueError("No items to evaluate.")
    task = items[0].task
    predictions = model.predict_batch(items)
    result: dict = {
        "task": task,
        "model": model.info(),
        "n_items": len(items),
        "metrics": {},
        "failure_taxonomy": failure_breakdown(items, predictions),
        "calibration": {
            "ece": expected_calibration_error(items, predictions),
        },
        "repro": {
            "seed": seed,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }
    if task == "matching":
        result["metrics"] = matching_scores(items, predictions)
    elif task == "compositional":
        result["metrics"] = accuracy_by_depth(items, predictions)
    else:
        # generic accuracy for other tasks
        from criterialogic.metrics.classification import accuracy
        pred_by_id = {p.item_id: p for p in predictions}
        result["metrics"] = {
            "accuracy": accuracy([it.gold for it in items],
                                 [pred_by_id[it.item_id].label for it in items])
        }
    # keep a small slice of the selective-accuracy curve for the report
    curve = selective_accuracy_curve(items, predictions)
    result["calibration"]["selective_accuracy_at_50pct_coverage"] = next(
        (pt["accuracy"] for pt in curve if pt["coverage"] >= 0.5), None
    )
    return result
`````
### FILE: criterialogic/leaderboard/__init__.py
`````python
"""Leaderboard: validate a submission file, then score & rank submissions."""
`````
### FILE: criterialogic/leaderboard/score.py
`````python
"""Score validated submissions with the benchmark task metrics and rank them."""
from __future__ import annotations
from criterialogic.eval.runner import run_task
from criterialogic.models.base import Model
from criterialogic.tasks.base import Item, Prediction
class _ReplayModel(Model):
    """Wrap a submission's predictions as a Model so it flows through the standard runner."""
    def __init__(self, name: str, predictions: list[Prediction]):
        self.name = name
        self._by_id = {p.item_id: p for p in predictions}
    def predict(self, item: Item) -> Prediction:
        return self._by_id[item.item_id]
def score_submission(submission: dict, items: list[Item]) -> dict:
    model = _ReplayModel(submission["model"], submission["predictions"])
    return run_task(model, items)
def rank(results: list[dict], task: str) -> list[dict]:
    """Rank result dicts by the task's headline metric (desc)."""
    def key(r):
        m = r["metrics"]
        if task == "matching":
            return m.get("overall_micro_f1", 0.0)
        if task == "compositional":
            return m.get("overall_accuracy", 0.0)
        return m.get("accuracy", 0.0)
    return sorted(results, key=key, reverse=True)
`````
### FILE: criterialogic/leaderboard/submit.py
`````python
"""Validate a leaderboard submission file.
A submission is JSON: {"model": "<name>", "task": "<task>",
"predictions": [{"item_id": ..., "label": bool, "confidence": float}, ...]}.
Validation checks the schema and that every evaluated item is covered.
"""
from __future__ import annotations
import json
from criterialogic.tasks.base import Prediction
class SubmissionError(ValueError):
    pass
def load_submission(path: str) -> dict:
    with open(path) as fh:
        data = json.load(fh)
    for key in ("model", "task", "predictions"):
        if key not in data:
            raise SubmissionError(f"Submission missing required field: '{key}'")
    data["predictions"] = [Prediction(**p) for p in data["predictions"]]
    return data
def validate_against_items(submission: dict, items) -> None:
    have = {p.item_id for p in submission["predictions"]}
    need = {it.item_id for it in items}
    missing, extra = need - have, have - need
    if missing:
        raise SubmissionError(f"Submission missing {len(missing)} predictions, e.g. {sorted(missing)[:3]}")
    if extra:
        raise SubmissionError(f"Submission has {len(extra)} unknown item_ids, e.g. {sorted(extra)[:3]}")
`````
### FILE: criterialogic/metrics/__init__.py
`````python
"""Metrics: classification, n2c2-style matching, logic-by-depth, calibration, extraction."""
`````
### FILE: criterialogic/metrics/calibration.py
`````python
"""Calibration & abstention metrics: Expected Calibration Error and selective accuracy."""
from __future__ import annotations
def expected_calibration_error(items, predictions, n_bins: int = 10) -> float:
    """ECE: weighted average gap between confidence and accuracy across equal-width bins."""
    pred_by_id = {p.item_id: p for p in predictions}
    rows = [(pred_by_id[it.item_id].confidence, pred_by_id[it.item_id].label == it.gold) for it in items]
    if not rows:
        return 0.0
    n = len(rows)
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        bucket = [(c, ok) for c, ok in rows if (lo < c <= hi) or (b == 0 and c == 0.0)]
        if not bucket:
            continue
        conf = sum(c for c, _ in bucket) / len(bucket)
        acc = sum(1 for _, ok in bucket if ok) / len(bucket)
        ece += (len(bucket) / n) * abs(acc - conf)
    return ece
def selective_accuracy_curve(items, predictions) -> list[dict]:
    """Accuracy vs coverage: sort by confidence desc, report accuracy on the top-k kept."""
    pred_by_id = {p.item_id: p for p in predictions}
    rows = sorted(
        [(pred_by_id[it.item_id].confidence, pred_by_id[it.item_id].label == it.gold) for it in items],
        key=lambda r: r[0], reverse=True,
    )
    curve, correct = [], 0
    for k, (_, ok) in enumerate(rows, start=1):
        correct += int(ok)
        curve.append({"coverage": k / len(rows), "accuracy": correct / k})
    return curve
`````
### FILE: criterialogic/metrics/classification.py
`````python
"""Precision / recall / F1 for binary and multi-class labels (no sklearn dependency)."""
from __future__ import annotations
from collections import defaultdict
def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"precision": p, "recall": r, "f1": f, "support": tp + fn}
def per_class_prf(y_true: list, y_pred: list) -> dict:
    """Per-class precision/recall/F1 over arbitrary hashable labels."""
    assert len(y_true) == len(y_pred)
    tp: defaultdict = defaultdict(int)
    fp: defaultdict = defaultdict(int)
    fn: defaultdict = defaultdict(int)
    labels = set(y_true) | set(y_pred)
    for t, p in zip(y_true, y_pred):
        if t == p:
            tp[t] += 1
        else:
            fp[p] += 1
            fn[t] += 1
    return {lab: _prf(tp[lab], fp[lab], fn[lab]) for lab in sorted(labels, key=str)}
def macro_f1(y_true: list, y_pred: list) -> float:
    per = per_class_prf(y_true, y_pred)
    return sum(v["f1"] for v in per.values()) / len(per) if per else 0.0
def micro_f1(y_true: list, y_pred: list) -> float:
    tp = fp = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == p:
            tp += 1
        else:
            fp += 1
            fn += 1
    return _prf(tp, fp, fn)["f1"]
def accuracy(y_true: list, y_pred: list) -> float:
    if not y_true:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
`````
### FILE: criterialogic/metrics/extraction.py
`````python
"""Task A scoring: entity F1, relation F1, and logical-form exact match.
Entity/relation F1 are set-based P/R/F1 over (text, type) and (operator, child)
tuples. Logical-form exact match compares *canonicalised* expressions, so trivial
operand reorderings or double negation do not count as mismatches.
"""
from __future__ import annotations
from criterialogic.metrics.classification import _prf
from criterialogic.schema.logical_form import Atom, BooleanGroup, Expression, LogicalForm, Not, canonicalize
def _set_prf(gold: set, pred: set) -> dict:
    tp = len(gold & pred)
    return _prf(tp, len(pred - gold), len(gold - pred))
def entity_set(expr: Expression) -> set:
    if isinstance(expr, Atom):
        return {(expr.entity.text, expr.entity.type.value)}
    if isinstance(expr, Not):
        return entity_set(expr.operand)
    if isinstance(expr, BooleanGroup):
        out: set = set()
        for op in expr.operands:
            out |= entity_set(op)
        return out
    raise TypeError(type(expr))
def entity_f1(gold: LogicalForm, pred: LogicalForm) -> dict:
    return _set_prf(entity_set(gold.expression), entity_set(pred.expression))
def logical_form_exact_match(gold: LogicalForm, pred: LogicalForm) -> bool:
    """True iff the canonicalised expressions are identical (and polarity matches)."""
    if gold.polarity != pred.polarity:
        return False
    return canonicalize(gold.expression).model_dump_json() == canonicalize(pred.expression).model_dump_json()
`````
### FILE: criterialogic/metrics/logic.py
`````python
"""Task D scoring: accuracy stratified by logical nesting depth.
The headline result the paper reports is how accuracy *degrades* as nesting depth
increases — so we return accuracy per depth plus the overall figure.
"""
from __future__ import annotations
from collections import defaultdict
from criterialogic.metrics.classification import accuracy
def accuracy_by_depth(items, predictions) -> dict:
    pred_by_id = {p.item_id: p for p in predictions}
    by_depth_true: dict[int, list] = defaultdict(list)
    by_depth_pred: dict[int, list] = defaultdict(list)
    for it in items:
        by_depth_true[it.depth].append(it.gold)
        by_depth_pred[it.depth].append(pred_by_id[it.item_id].label)
    per_depth = {
        d: {"accuracy": accuracy(by_depth_true[d], by_depth_pred[d]), "n": len(by_depth_true[d])}
        for d in sorted(by_depth_true)
    }
    all_true = [it.gold for it in items]
    all_pred = [pred_by_id[it.item_id].label for it in items]
    return {"overall_accuracy": accuracy(all_true, all_pred), "by_depth": per_depth}
`````
### FILE: criterialogic/metrics/matching.py
`````python
"""n2c2-*style* scoring for Task C: micro & macro F1 over the met/not-met labels,
plus a per-criterion breakdown.
Note on "official" parity: the n2c2 2018 Track-1 organizers' scorer reports
micro- and macro-averaged F1 computed over the per-criterion, per-class results.
The ``overall_macro_f1`` returned here is a macro over the two label *classes*
(met / not-met), which is a defensible but NOT bit-identical statistic. Exact
parity with the released official scorer is a TODO; until then we describe these
as n2c2-style. The per-criterion micro-F1 table is the primary diagnostic the
paper's per-criterion analysis relies on.
"""
from __future__ import annotations
from collections import defaultdict
from criterialogic.metrics.classification import macro_f1, micro_f1, per_class_prf
def matching_scores(items, predictions) -> dict:
    """`items`: list[Item]; `predictions`: list[Prediction] (aligned by item_id)."""
    pred_by_id = {p.item_id: p for p in predictions}
    y_true = [it.gold for it in items]
    y_pred = [pred_by_id[it.item_id].label for it in items]
    # per-criterion micro-F1 (treat "met" as the positive class)
    by_crit_true: dict[str, list] = defaultdict(list)
    by_crit_pred: dict[str, list] = defaultdict(list)
    for it in items:
        by_crit_true[it.group].append(it.gold)
        by_crit_pred[it.group].append(pred_by_id[it.item_id].label)
    per_criterion = {
        tag: {"micro_f1": micro_f1(by_crit_true[tag], by_crit_pred[tag]),
              "n": len(by_crit_true[tag])}
        for tag in sorted(by_crit_true)
    }
    return {
        "overall_micro_f1": micro_f1(y_true, y_pred),
        "overall_macro_f1": macro_f1(y_true, y_pred),
        "n_items": len(items),
        "per_criterion": per_criterion,
        "per_label": per_class_prf(y_true, y_pred),
    }
`````
### FILE: criterialogic/models/__init__.py
`````python
"""Baseline adapters behind one pluggable Model interface (the adoption lever)."""
from criterialogic.models.base import Model  # noqa: F401
from criterialogic.models.llm_api import OpenAILLMModel
from criterialogic.models.naive import NegationBlindModel
from criterialogic.models.rule_based import RuleBasedModel
REGISTRY = {
    "rule_based": RuleBasedModel,
    "negation_blind": NegationBlindModel,
    "openai": OpenAILLMModel,
}
# Models that need no API key / network — used as the default demo sweep.
OFFLINE_MODELS = ["rule_based", "negation_blind"]
`````
### FILE: criterialogic/models/base.py
`````python
"""The single Model interface every baseline / submission implements.
One interface is the biggest lever for leaderboard adoption (spec §8): anyone
can plug in a system by subclassing `Model` and implementing `predict`.
"""
from __future__ import annotations
import abc
from criterialogic.tasks.base import Item, Prediction
class Model(abc.ABC):
    """Predict a met/not-met decision (+ confidence) for a benchmark Item."""
    #: short identifier used in result files / the leaderboard
    name: str = "model"
    @abc.abstractmethod
    def predict(self, item: Item) -> Prediction:
        """Return a Prediction for one Item. Must set item_id, label, confidence."""
    def predict_batch(self, items: list[Item]) -> list[Prediction]:
        return [self.predict(item) for item in items]
    def info(self) -> dict:
        """Reproducibility metadata logged into every result file."""
        return {"name": self.name, "type": type(self).__name__}
`````
### FILE: criterialogic/models/encoder.py
`````python
"""Fine-tuned encoder baseline (BioClinicalBERT / PubMedBERT) — interface stub.
Implements the Model contract; the body is a TODO requiring `transformers`,
`torch`, and a fine-tuned checkpoint (Tasks B–C). Kept import-safe so the demo
runs without heavy ML dependencies installed.
"""
from __future__ import annotations
from criterialogic.models.base import Model
from criterialogic.tasks.base import Item, Prediction
class EncoderModel(Model):
    name = "encoder"
    def __init__(self, checkpoint: str = "emilyalsentzer/Bio_ClinicalBERT"):
        self.checkpoint = checkpoint
        # TODO: lazy-load tokenizer + classification head from `checkpoint`.
    def predict(self, item: Item) -> Prediction:  # pragma: no cover
        raise NotImplementedError(
            "EncoderModel requires transformers/torch and a fine-tuned head. "
            "Install the [encoder] extra and load a checkpoint. See models/encoder.py."
        )
`````
### FILE: criterialogic/models/llm_api.py
`````python
"""OpenAI LLM baseline for CriteriaLogic.
Renders each item's criterion (its logical structure) and the patient's facts into a
prompt, asks an OpenAI chat model for a met/not-met decision plus a calibrated
confidence, and returns a Prediction. Designed for real benchmark runs:
* JSON-mode output + robust parsing (survives stray prose / code fences).
* temperature=0 by default for reproducibility; auto-dropped for models that reject it.
* On-disk response cache keyed by (model, prompt) so re-runs are free and resumable.
* Retries on transient/rate-limit errors, and per-item graceful failure (a single bad
  call yields a low-confidence abstain rather than aborting the whole evaluation).
Setup:  pip install -e ".[llm]"  and  export OPENAI_API_KEY=...
Choose the model with the CRITERIALOGIC_LLM_MODEL env var (default: gpt-4o-mini) or the
`model=` constructor argument. Run e.g.:  python scripts/run_eval.py --task compositional --model openai
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path
from criterialogic.models.base import Model
from criterialogic.oracle import PatientFacts
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Expression,
    LogicalForm,
    Not,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
)
from criterialogic.tasks.base import Item, Prediction
DEFAULT_MODEL = os.environ.get("CRITERIALOGIC_LLM_MODEL", "gpt-4o-mini")
_SYSTEM = (
    "You are a careful clinical-trial eligibility assessor. You are given one eligibility "
    "CRITERION (which may nest AND / OR / NOT, temporal windows, and numeric thresholds) and a "
    "PATIENT described by a set of facts. Decide whether the patient SATISFIES the criterion. "
    "Reason about the logical structure exactly: respect negation and polarity, AND vs OR, "
    "temporal windows, and numeric boundaries. Any entity not listed for the patient is undocumented; "
    "if the criterion's truth cannot be determined from the facts, choose the value the criterion "
    "implies for an undocumented finding (usually not satisfied) and lower your confidence. "
    'Respond with ONLY a JSON object: {"label": <true|false>, "confidence": <0.0-1.0>, '
    '"rationale": "<one sentence>"}. label=true means the criterion IS satisfied. confidence is your '
    "calibrated probability that the label is correct."
)
_NUM_SYM = {
    Comparator.LT: "< {v}", Comparator.LE: "<= {v}", Comparator.GT: "> {v}",
    Comparator.GE: ">= {v}", Comparator.EQ: "= {v}", Comparator.NE: "!= {v}",
}
# --------------------------------------------------------------------------- #
# Rendering criterion + patient into readable prompt text
# --------------------------------------------------------------------------- #
def _render_numeric(nc: NumericConstraint) -> str:
    unit = f" {nc.unit}" if nc.unit else ""
    if nc.operator is Comparator.BETWEEN:
        return f"between {nc.value} and {nc.upper}{unit}"
    return _NUM_SYM[nc.operator].format(v=nc.value) + unit
def _render_temporal(tc: TemporalConstraint) -> str:
    if tc.operator is TemporalOp.CURRENT:
        return "current / ongoing"
    if tc.operator is TemporalOp.ANY_HISTORY:
        return "at any time in history"
    unit = tc.unit.value if tc.unit else ""
    if tc.operator is TemporalOp.WITHIN:
        return f"within the past {tc.value} {unit}"
    if tc.operator is TemporalOp.BEFORE:
        return f"before enrollment by {tc.value} {unit}"
    if tc.operator is TemporalOp.AFTER:
        return f"after enrollment by {tc.value} {unit}"
    if tc.operator is TemporalOp.FOR_AT_LEAST:
        return f"for at least {tc.value} {unit}"
    if tc.operator is TemporalOp.FOR_AT_MOST:
        return f"for at most {tc.value} {unit}"
    return tc.operator.value
def _render_atom(a: Atom) -> str:
    s = a.entity.text
    if a.numeric is not None:
        s += " " + _render_numeric(a.numeric)
    if a.temporal is not None:
        s += f" ({_render_temporal(a.temporal)})"
    return s
def render_expression(e: Expression) -> str:
    """Faithfully render a logical expression as a readable, parenthesized criterion."""
    if isinstance(e, Atom):
        return _render_atom(e)
    if isinstance(e, Not):
        return f"NOT ({render_expression(e.operand)})"
    if isinstance(e, BooleanGroup):
        joiner = " AND " if e.operator is BoolOp.AND else " OR "
        return "(" + joiner.join(render_expression(op) for op in e.operands) + ")"
    raise TypeError(type(e))
def render_criterion(form: LogicalForm) -> str:
    logic = render_expression(form.expression)
    text = (form.text or "").strip()
    polarity = form.polarity.value
    if text and not text.startswith("("):  # real criterion text present (n2c2); show both
        return f'"{text}"\nLogical form ({polarity} criterion): {logic}'
    return f"({polarity} criterion) {logic}"
def render_patient(facts: PatientFacts) -> str:
    if not facts.facts:
        return "No findings are documented for this patient."
    lines = []
    for name, f in facts.facts.items():
        if not f.present:
            lines.append(f"- {name}: absent / negative")
            continue
        bits = ["present"]
        if f.value is not None:
            bits.append(f"value = {f.value}")
        if f.current:
            bits.append("currently active")
        if f.days_ago is not None:
            bits.append(f"most recent occurrence ~{f.days_ago:g} days ago")
        lines.append(f"- {name}: " + ", ".join(bits))
    return "\n".join(lines)
def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):  # strip accidental code fences
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {raw[:200]!r}")
    return json.loads(raw[start : end + 1])
def _clamp(x, lo=0.0, hi=1.0) -> float:
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return 0.5
_TRUE = {"true", "yes", "met", "meets", "satisfied", "1"}
_FALSE = {"false", "no", "not met", "not_met", "unmet", "does not meet", "0"}
def _to_bool(v) -> bool:
    """Coerce a model's label to bool robustly (JSON bool, 0/1, or a string like "false")."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        t = v.strip().lower()
        if t in _TRUE:
            return True
        if t in _FALSE:
            return False
    raise ValueError(f"uninterpretable label: {v!r}")
class OpenAILLMModel(Model):
    name = "openai"
    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = 0.0,
        cache_dir: str | None = ".criterialogic_cache",
        max_retries: int = 4,
        client=None,
    ):
        self.model = model or DEFAULT_MODEL
        self.temperature = temperature
        self.max_retries = max_retries
        self._client = client
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
    def info(self) -> dict:
        return {"name": self.name, "provider": "openai", "model": self.model,
                "temperature": self.temperature}
    # --- API plumbing (monkeypatchable in tests) --------------------------- #
    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # lazy: no key/package needed to import this module
            self._client = OpenAI(max_retries=self.max_retries)
        return self._client
    def _complete(self, system: str, user: str) -> str:
        def _call(include_temp: bool):
            kwargs = dict(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                response_format={"type": "json_object"},
            )
            if include_temp and self.temperature is not None:
                kwargs["temperature"] = self.temperature
            return self._get_client().chat.completions.create(**kwargs)
        try:
            resp = _call(include_temp=True)
        except Exception as e:
            # Some reasoning models reject a custom temperature; drop it and stop sending it,
            # rather than failing (which would otherwise abstain on every item).
            if self.temperature is not None and "temperature" in str(e).lower():
                self.temperature = None
                resp = _call(include_temp=False)
            else:
                raise
        return resp.choices[0].message.content or ""
    def _cached_complete(self, system: str, user: str) -> str:
        if not self._cache_dir:
            return self._retry_complete(system, user)
        key = hashlib.sha256(f"{self.model}\x00{system}\x00{user}".encode()).hexdigest()
        cpath = self._cache_dir / f"{key}.json"
        if cpath.exists():
            return json.loads(cpath.read_text())["response"]
        out = self._retry_complete(system, user)
        cpath.write_text(json.dumps({"model": self.model, "response": out}))
        return out
    def _retry_complete(self, system: str, user: str) -> str:
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            try:
                return self._complete(system, user)
            except Exception:
                if attempt == self.max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")
    def _build_prompt(self, item: Item) -> tuple[str, str]:
        user = (
            f"CRITERION:\n{render_criterion(item.criterion)}\n\n"
            f"PATIENT FACTS (entities not listed are undocumented):\n{render_patient(item.facts)}\n\n"
            "Does the patient satisfy the criterion?"
        )
        return _SYSTEM, user
    def predict(self, item: Item) -> Prediction:
        system, user = self._build_prompt(item)
        try:
            data = _parse_json(self._cached_complete(system, user))
            return Prediction(
                item_id=item.item_id,
                label=_to_bool(data["label"]),
                confidence=_clamp(data.get("confidence", 0.5)),
                rationale=(data.get("rationale") or None),
            )
        except Exception as e:  # per-item graceful failure -> abstain, don't crash the run
            return Prediction(item_id=item.item_id, label=False, confidence=0.0,
                              abstain=True, rationale=f"api/parse error: {type(e).__name__}: {e}")
# Backwards-compatible alias for the previous stub name.
ApiLLMModel = OpenAILLMModel
`````
### FILE: criterialogic/models/llm_local.py
`````python
"""Open-weight LLM baseline (Llama / Mistral / Qwen via HF or vLLM) — interface stub.
Same contract as ApiLLMModel; the body is a TODO requiring a local runtime.
Import-safe so the demo runs without a GPU stack.
"""
from __future__ import annotations
from criterialogic.models.base import Model
from criterialogic.tasks.base import Item, Prediction
class LocalLLMModel(Model):
    name = "llm_local"
    def __init__(self, model: str = "meta-llama/Llama-3.1-8B-Instruct", backend: str = "hf"):
        self.model = model
        self.backend = backend
    def predict(self, item: Item) -> Prediction:  # pragma: no cover
        raise NotImplementedError(
            "LocalLLMModel requires a HF/vLLM runtime. Load `model`, prompt it on the "
            "criterion + note, parse {label, confidence}. See models/llm_local.py."
        )
`````
### FILE: criterialogic/models/naive.py
`````python
"""A deliberately negation-blind baseline (illustrative, not for the leaderboard).
It strips NOT nodes and collapses OR to its first operand, so it systematically
makes *negation/polarity* and *logical-composition* errors. Its purpose is to
make the demo's metrics and reasoning-failure taxonomy non-trivial — i.e. to show
the framework detecting and categorising real error patterns.
"""
from __future__ import annotations
from criterialogic.models.base import Model
from criterialogic.oracle import evaluate
from criterialogic.schema.logical_form import Atom, BooleanGroup, BoolOp, Expression, Not
from criterialogic.tasks.base import Item, Prediction
def _strip(expr: Expression) -> Expression:
    if isinstance(expr, Atom):
        return expr
    if isinstance(expr, Not):
        return _strip(expr.operand)  # bug: ignores negation
    if isinstance(expr, BooleanGroup):
        kept = [_strip(op) for op in expr.operands]
        if expr.operator is BoolOp.OR:
            return kept[0]  # bug: treats OR as "first operand only"
        return BooleanGroup(operator=BoolOp.AND, operands=kept)
    raise TypeError(type(expr))
class NegationBlindModel(Model):
    name = "negation_blind"
    def predict(self, item: Item) -> Prediction:
        value = evaluate(_strip(item.criterion.expression), item.facts)
        label = bool(value) if value is not None else False
        return Prediction(item_id=item.item_id, label=label, confidence=0.7)
`````
### FILE: criterialogic/models/rule_based.py
`````python
"""Rule-based baseline — the deterministic floor of the ladder.
It evaluates the *already-structured* LogicalForm against the patient facts with
the oracle's three-valued logic. On structured synthetic input it is effectively
an oracle (≈ perfect); on real text it would first require Task-A parsing, which
is where rule-based systems lose ground. Confidence is 1.0 for decided cases and
0.5 for unknowns (which it resolves to not-met).
"""
from __future__ import annotations
from criterialogic.models.base import Model
from criterialogic.oracle import evaluate
from criterialogic.tasks.base import Item, Prediction
class RuleBasedModel(Model):
    name = "rule_based"
    def predict(self, item: Item) -> Prediction:
        value = evaluate(item.criterion.expression, item.facts)
        if value is None:
            return Prediction(item_id=item.item_id, label=False, confidence=0.5,
                              abstain=False, rationale="unknown -> not met")
        return Prediction(item_id=item.item_id, label=value, confidence=1.0)
`````
### FILE: criterialogic/oracle.py
`````python
"""oracle.py — deterministic ground-truth evaluator for a LogicalForm.
Given a structured ``PatientFacts`` record, ``evaluate`` decides whether a
criterion's logical expression is satisfied. It serves two roles:
1. The **ground-truth oracle** for the synthetic Task C/D items (the label a
   perfect system should produce).
2. The engine behind the **rule-based baseline** (the deterministic floor of
   the baseline ladder), which evaluates an already-structured form.
Three-valued logic is used: a leaf whose fact is absent evaluates to ``None``
(*unknown*). ``None`` propagates through AND/OR with Kleene semantics so that
"unknown" is never silently treated as "not met".
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Expression,
    LogicalForm,
    Not,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
)
_TO_DAYS = {TimeUnit.DAYS: 1.0, TimeUnit.WEEKS: 7.0, TimeUnit.MONTHS: 30.4375, TimeUnit.YEARS: 365.25}
class Fact(BaseModel):
    """A single structured fact about a patient, keyed by entity surface text."""
    present: bool = True
    value: float | None = None  # measured value for measurement/observation/person entities
    days_ago: float | None = None  # recency of the most recent occurrence, relative to anchor
    current: bool = False  # is the state ongoing/active at the anchor
class PatientFacts(BaseModel):
    """A synthetic (or harmonized) structured patient record: entity text -> Fact."""
    record_id: str
    facts: dict[str, Fact] = Field(default_factory=dict)
    def get(self, entity_text: str) -> Fact | None:
        return self.facts.get(entity_text)
# --------------------------------------------------------------------------- #
# Kleene three-valued connectives
# --------------------------------------------------------------------------- #
def _and(values: list[bool | None]) -> bool | None:
    if any(v is False for v in values):
        return False
    if any(v is None for v in values):
        return None
    return True
def _or(values: list[bool | None]) -> bool | None:
    if any(v is True for v in values):
        return True
    if any(v is None for v in values):
        return None
    return False
def _check_numeric(c: NumericConstraint, x: float) -> bool:
    if c.operator is Comparator.LT:
        return x < c.value
    if c.operator is Comparator.LE:
        return x <= c.value
    if c.operator is Comparator.GT:
        return x > c.value
    if c.operator is Comparator.GE:
        return x >= c.value
    if c.operator is Comparator.EQ:
        return x == c.value
    if c.operator is Comparator.NE:
        return x != c.value
    if c.operator is Comparator.BETWEEN:
        lo = x >= c.value if c.lower_inclusive else x > c.value
        hi = x <= c.upper if c.upper_inclusive else x < c.upper
        return lo and hi
    raise ValueError(f"Unhandled comparator {c.operator}")
def _check_temporal(t: TemporalConstraint, fact: Fact) -> bool | None:
    if t.operator is TemporalOp.CURRENT:
        return fact.current
    if t.operator is TemporalOp.ANY_HISTORY:
        return fact.present
    # windowed operators need a recency
    if fact.days_ago is None:
        return None
    window_days = (t.value or 0) * _TO_DAYS[t.unit]
    if t.operator in (TemporalOp.WITHIN, TemporalOp.BEFORE, TemporalOp.FOR_AT_MOST):
        return fact.days_ago <= window_days
    if t.operator in (TemporalOp.AFTER, TemporalOp.FOR_AT_LEAST):
        return fact.days_ago >= window_days
    raise ValueError(f"Unhandled temporal operator {t.operator}")
def _eval_atom(atom: Atom, facts: PatientFacts) -> bool | None:
    fact = facts.get(atom.entity.text)
    if fact is None or not fact.present:
        # numeric/temporal questions about an absent entity are unknown vs. false:
        # an absent condition is "not met" (False); an absent measurement is "unknown" (None).
        if fact is None and atom.numeric is not None:
            return None
        return False
    result: bool | None = True
    if atom.numeric is not None:
        if fact.value is None:
            return None
        result = _and([result, _check_numeric(atom.numeric, fact.value)])
    if atom.temporal is not None:
        result = _and([result, _check_temporal(atom.temporal, fact)])
    return result
def evaluate(expr: Expression, facts: PatientFacts) -> bool | None:
    """Three-valued evaluation of an expression against patient facts."""
    if isinstance(expr, Atom):
        return _eval_atom(expr, facts)
    if isinstance(expr, Not):
        inner = evaluate(expr.operand, facts)
        return None if inner is None else (not inner)
    if isinstance(expr, BooleanGroup):
        vals = [evaluate(op, facts) for op in expr.operands]
        return _and(vals) if expr.operator is BoolOp.AND else _or(vals)
    raise TypeError(f"Unknown expression node: {type(expr)!r}")
def is_met(form: LogicalForm, facts: PatientFacts, unknown_is_met: bool = False) -> bool:
    """Collapse three-valued evaluation to a met/not-met decision.
    Polarity is preserved upstream; this returns truth of the *expression*.
    Unknown resolves to ``unknown_is_met`` (default: not met).
    """
    v = evaluate(form.expression, facts)
    return unknown_is_met if v is None else v
`````
### FILE: criterialogic/schema/__init__.py
`````python
"""CriteriaLogic schema package: the harmonized logical form + validators."""
from criterialogic.schema.logical_form import (  # noqa: F401
    SCHEMA_VERSION,
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Entity,
    EntityType,
    Expression,
    LogicalForm,
    Not,
    NumericConstraint,
    Polarity,
    Source,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
    canonicalize,
)
`````
### FILE: criterialogic/schema/logical_form.py
`````python
"""logical_form.py — CriteriaLogic harmonized logical form.
A canonical, source-agnostic representation of a single clinical-trial
eligibility criterion. Both the **Chia** corpus (entity/relation annotations
with AND/OR/negation/value/temporal) and the **n2c2 2018** cohort-selection
criteria (13 patient-level met/not-met rules) map onto this one model, so every
downstream benchmark task — (A) structuring, (B) typing & polarity,
(C) patient–criterion matching, (D) compositional-logic stress test — operates
on a single schema.
Design goals
------------
- **Expressive:** nested AND/OR/NOT scoping plus the four constraint types
  the benchmark targets (entity, temporal, numeric, polarity).
- **Canonical:** one normal form per logic (`canonicalize`: operand sorting,
  same-operator flattening, double-negation collapse, dedupe) so Task A's
  logical-form *exact match* is meaningful rather than penalizing trivial
  reorderings.
- **Round-trippable:** pure pydantic v2 — `model_dump_json()` /
  `model_validate_json()` reconstruct an identical object.
- **Lossless to source:** criterion-level inclusion/exclusion polarity is kept
  as a label and is *not* folded into the logical expression (see TRADEOFFS).
Constraints: public/synthetic data only; solo/first-authorship project.
Intrinsic structural validation lives here on the models; corpus-level checks
(cross-criterion, leakage) belong in the sibling `validators.py`.
"""
from __future__ import annotations
from enum import Enum
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
SCHEMA_VERSION = "0.1.0"
# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class Polarity(str, Enum):
    """Which list the criterion was drawn from. Distinct from logical NOT."""
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
class Source(str, Enum):
    """Provenance — drives licensing / redistribution handling downstream."""
    CHIA = "chia"
    N2C2_2018 = "n2c2_2018"
    CTGOV_SYNTHETIC = "ctgov_synthetic"  # Task D compositional stress-test set
class EntityType(str, Enum):
    """Coarse clinical concept type; superset covering Chia + n2c2."""
    CONDITION = "condition"
    DRUG = "drug"
    PROCEDURE = "procedure"
    MEASUREMENT = "measurement"  # lab/vital carrying a numeric value (HbA1c, creatinine)
    OBSERVATION = "observation"
    PERSON = "person"  # demographics (age, sex)
    DEVICE = "device"
    VISIT = "visit"
    LIFESTYLE = "lifestyle"
    OTHER = "other"
class BoolOp(str, Enum):
    AND = "and"
    OR = "or"
class TemporalOp(str, Enum):
    """Temporal relation between the predicate and a reference anchor."""
    WITHIN = "within"  # occurred within `value` `unit` of the anchor (lookback window)
    BEFORE = "before"
    AFTER = "after"
    FOR_AT_LEAST = "for_at_least"  # state has persisted >= duration
    FOR_AT_MOST = "for_at_most"
    CURRENT = "current"  # ongoing/active at the anchor (no magnitude)
    ANY_HISTORY = "any_history"  # ever, unbounded (no magnitude)
class TimeUnit(str, Enum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"
class Comparator(str, Enum):
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    EQ = "eq"
    NE = "ne"
    BETWEEN = "between"
_WINDOWED_TEMPORAL = {
    TemporalOp.WITHIN,
    TemporalOp.BEFORE,
    TemporalOp.AFTER,
    TemporalOp.FOR_AT_LEAST,
    TemporalOp.FOR_AT_MOST,
}
_BARE_TEMPORAL = {TemporalOp.CURRENT, TemporalOp.ANY_HISTORY}
_NUMERIC_ENTITY_TYPES = {
    EntityType.MEASUREMENT,
    EntityType.OBSERVATION,
    EntityType.PERSON,
}
# --------------------------------------------------------------------------- #
# Leaf payloads
# --------------------------------------------------------------------------- #
class Entity(BaseModel):
    """A single clinical concept — the noun a predicate is about."""
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., description="Surface form as annotated in the source.")
    type: EntityType = EntityType.OTHER
    codes: dict[str, str] = Field(
        default_factory=dict,
        description="Optional ontology codes, e.g. {'UMLS': 'C0011860'}. One code per system.",
    )
    @field_validator("text")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Entity.text must be non-empty.")
        return v
class TemporalConstraint(BaseModel):
    """A time qualifier on a predicate, e.g. 'within 6 months of enrollment'."""
    model_config = ConfigDict(extra="forbid")
    operator: TemporalOp
    value: float | None = Field(default=None, description="Magnitude for windowed operators.")
    unit: TimeUnit | None = None
    anchor: str = Field(default="enrollment", description="Reference event the window is measured from.")
    @model_validator(mode="after")
    def _check_magnitude(self) -> TemporalConstraint:
        if self.operator in _WINDOWED_TEMPORAL:
            if self.value is None or self.unit is None:
                raise ValueError(f"Temporal operator '{self.operator.value}' requires value and unit.")
            if self.value <= 0:
                raise ValueError("Temporal value must be positive.")
        if self.operator in _BARE_TEMPORAL and (self.value is not None or self.unit is not None):
            raise ValueError(f"Temporal operator '{self.operator.value}' must not carry value/unit.")
        return self
class NumericConstraint(BaseModel):
    """A numeric threshold on a measurement, e.g. 'HbA1c between 6.5 and 9.5 %'."""
    model_config = ConfigDict(extra="forbid")
    operator: Comparator
    value: float = Field(..., description="The bound; the LOWER bound when operator == BETWEEN.")
    upper: float | None = Field(default=None, description="Upper bound; required iff BETWEEN.")
    unit: str | None = Field(default=None, description="e.g. '%', 'mg/dL', 'years', 'kg/m^2'.")
    lower_inclusive: bool = True
    upper_inclusive: bool = True
    @model_validator(mode="after")
    def _check_bounds(self) -> NumericConstraint:
        if self.operator is Comparator.BETWEEN:
            if self.upper is None:
                raise ValueError("BETWEEN requires `upper`.")
            if self.upper <= self.value:
                raise ValueError("BETWEEN requires upper > value (the lower bound).")
        elif self.upper is not None:
            raise ValueError("`upper` is only valid with operator == BETWEEN.")
        return self
# --------------------------------------------------------------------------- #
# Expression tree — a discriminated union on `node_type`
# --------------------------------------------------------------------------- #
class Atom(BaseModel):
    """A single, optionally time- and value-qualified predicate about one entity."""
    model_config = ConfigDict(extra="forbid")
    node_type: Literal["atom"] = "atom"
    entity: Entity
    temporal: TemporalConstraint | None = None
    numeric: NumericConstraint | None = None
    @model_validator(mode="after")
    def _numeric_target(self) -> Atom:
        if self.numeric is not None and self.entity.type not in _NUMERIC_ENTITY_TYPES:
            raise ValueError(
                f"Numeric constraint attached to non-measurable entity type "
                f"'{self.entity.type.value}'; expected measurement/observation/person."
            )
        return self
class Not(BaseModel):
    """Logical negation of a sub-expression. Scopes over an atom OR a group."""
    model_config = ConfigDict(extra="forbid")
    node_type: Literal["not"] = "not"
    operand: Expression
class BooleanGroup(BaseModel):
    """N-ary AND / OR over >= 2 sub-expressions."""
    model_config = ConfigDict(extra="forbid")
    node_type: Literal["group"] = "group"
    operator: BoolOp
    operands: list[Expression]
    @field_validator("operands")
    @classmethod
    def _min_two(cls, v: list) -> list:
        if len(v) < 2:
            raise ValueError("BooleanGroup requires >= 2 operands; unwrap singletons into the parent.")
        return v
# The recursive node type. Pydantic resolves the forward refs via model_rebuild() below.
Expression = Annotated[
    Atom | BooleanGroup | Not,
    Field(discriminator="node_type"),
]
# --------------------------------------------------------------------------- #
# Top-level criterion
# --------------------------------------------------------------------------- #
class LogicalForm(BaseModel):
    """Harmonized representation of one eligibility criterion (the unit of the benchmark)."""
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION
    criterion_id: str = Field(..., description="Stable id, e.g. 'n2c2:MI-6MOS' or 'chia:NCT00000000:42'.")
    source: Source
    polarity: Polarity
    text: str = Field(..., description="Verbatim criterion text from the source.")
    expression: Expression
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form provenance (trial id, span offsets, ...)."
    )
    @field_validator("criterion_id", "text")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must be non-empty.")
        return v
    def canonical(self) -> LogicalForm:
        """Return a copy with the expression in canonical normal form (see `canonicalize`)."""
        return self.model_copy(update={"expression": canonicalize(self.expression)})
# Resolve forward references for the recursive discriminated union.
Not.model_rebuild()
BooleanGroup.model_rebuild()
LogicalForm.model_rebuild()
# --------------------------------------------------------------------------- #
# Canonicalization — the normal form Task A scores exact-match against
# --------------------------------------------------------------------------- #
def _key(expr: Expression) -> str:
    """Deterministic sort/dedupe key for a node (AND/OR are commutative)."""
    return expr.model_dump_json()
def canonicalize(expr: Expression) -> Expression:
    """Reduce an expression to a single normal form for exact-match comparison.
    Idempotent. Applies, recursively:
      * flatten nested same-operator groups   (A AND (B AND C)) -> AND(A, B, C)
      * drop structurally duplicate operands
      * sort operands by serialized form
      * collapse double negation              NOT(NOT x) -> x
      * unwrap a group left with one operand   AND(A) -> A
    """
    if isinstance(expr, Atom):
        return expr.model_copy(deep=True)
    if isinstance(expr, Not):
        inner = canonicalize(expr.operand)
        if isinstance(inner, Not):  # NOT(NOT x) -> x
            return inner.operand
        return Not(operand=inner)
    if isinstance(expr, BooleanGroup):
        flattened: list[Expression] = []
        for op in expr.operands:
            c = canonicalize(op)
            if isinstance(c, BooleanGroup) and c.operator == expr.operator:
                flattened.extend(c.operands)  # absorb same-operator child
            else:
                flattened.append(c)
        seen: set[str] = set()
        unique: list[Expression] = []
        for c in flattened:
            k = _key(c)
            if k not in seen:
                seen.add(k)
                unique.append(c)
        unique.sort(key=_key)
        if len(unique) == 1:  # everything collapsed/deduped to one child
            return unique[0]
        return BooleanGroup(operator=expr.operator, operands=unique)
    raise TypeError(f"Unknown expression node: {type(expr)!r}")
# --------------------------------------------------------------------------- #
# Worked examples (also serve as smoke tests under __main__)
# --------------------------------------------------------------------------- #
def example_simple_inclusion() -> LogicalForm:
    """Simple inclusion: a single entity + one numeric constraint.
    'Age 18 years or older.'  (maps cleanly from an n2c2-style demographic rule)
    """
    return LogicalForm(
        criterion_id="ctgov:demo:age-18",
        source=Source.CTGOV_SYNTHETIC,
        polarity=Polarity.INCLUSION,
        text="Age 18 years or older.",
        expression=Atom(
            entity=Entity(text="age", type=EntityType.PERSON),
            numeric=NumericConstraint(operator=Comparator.GE, value=18, unit="years"),
        ),
    )
def example_nested_compound() -> LogicalForm:
    """Nested AND/OR/NOT exercising temporal + numeric constraints together.
    'Type 2 diabetes with HbA1c between 6.5% and 9.5%, AND either myocardial
     infarction within the past 6 months OR current aspirin therapy, AND no
     diabetic ketoacidosis within the past year.'
    """
    return LogicalForm(
        criterion_id="ctgov:demo:t2dm-composite",
        source=Source.CTGOV_SYNTHETIC,
        polarity=Polarity.INCLUSION,
        text=(
            "Type 2 diabetes mellitus with HbA1c between 6.5% and 9.5%, and either "
            "myocardial infarction within the past 6 months or current aspirin therapy, "
            "and no diabetic ketoacidosis within the past year."
        ),
        expression=BooleanGroup(
            operator=BoolOp.AND,
            operands=[
                Atom(entity=Entity(text="type 2 diabetes mellitus", type=EntityType.CONDITION)),
                Atom(
                    entity=Entity(text="HbA1c", type=EntityType.MEASUREMENT),
                    numeric=NumericConstraint(operator=Comparator.BETWEEN, value=6.5, upper=9.5, unit="%"),
                ),
                BooleanGroup(
                    operator=BoolOp.OR,
                    operands=[
                        Atom(
                            entity=Entity(text="myocardial infarction", type=EntityType.CONDITION),
                            temporal=TemporalConstraint(
                                operator=TemporalOp.WITHIN, value=6, unit=TimeUnit.MONTHS, anchor="enrollment"
                            ),
                        ),
                        Atom(
                            entity=Entity(text="aspirin", type=EntityType.DRUG),
                            temporal=TemporalConstraint(operator=TemporalOp.CURRENT),
                        ),
                    ],
                ),
                Not(
                    operand=Atom(
                        entity=Entity(text="diabetic ketoacidosis", type=EntityType.CONDITION),
                        temporal=TemporalConstraint(
                            operator=TemporalOp.WITHIN, value=1, unit=TimeUnit.YEARS, anchor="enrollment"
                        ),
                    )
                ),
            ],
        ),
    )
if __name__ == "__main__":
    for lf in (example_simple_inclusion(), example_nested_compound()):
        blob = lf.model_dump_json(indent=2)
        # Round-trip invariant: JSON -> object -> JSON is identical.
        assert LogicalForm.model_validate_json(blob).model_dump_json(indent=2) == blob
        print(blob)
        print("-" * 70)
    # Canonicalization is idempotent and order/duplication invariant.
    c = example_nested_compound().canonical()
    assert c.canonical().model_dump_json() == c.model_dump_json()
    print("OK: round-trip + idempotent canonicalization")
`````
### FILE: criterialogic/schema/validators.py
`````python
"""Corpus-level validation (beyond the intrinsic per-model checks in logical_form).
These run over a *collection* of LogicalForm records, e.g. after harmonization,
to catch problems the single-record pydantic validators cannot see: duplicate
ids, schema-version drift, and (for split hygiene) trial-id leakage.
"""
from __future__ import annotations
from collections import Counter
from criterialogic.schema.logical_form import SCHEMA_VERSION, LogicalForm
class CorpusValidationError(ValueError):
    """Raised when a collection of LogicalForm records is internally inconsistent."""
def check_unique_ids(forms: list[LogicalForm]) -> None:
    """Every ``criterion_id`` must be unique across the corpus."""
    dupes = [cid for cid, n in Counter(f.criterion_id for f in forms).items() if n > 1]
    if dupes:
        raise CorpusValidationError(f"Duplicate criterion_id(s): {sorted(dupes)}")
def check_schema_version(forms: list[LogicalForm], expected: str = SCHEMA_VERSION) -> None:
    """All records should share one schema version (no silent format drift)."""
    bad = {f.schema_version for f in forms if f.schema_version != expected}
    if bad:
        raise CorpusValidationError(f"Mixed schema versions present: {sorted(bad)} (expected {expected}).")
def check_no_trial_leakage(train: list[LogicalForm], test: list[LogicalForm], key: str = "trial_id") -> None:
    """No trial id may appear in both splits (prevents train/test contamination)."""
    tr = {f.metadata.get(key) for f in train if f.metadata.get(key)}
    te = {f.metadata.get(key) for f in test if f.metadata.get(key)}
    overlap = tr & te
    if overlap:
        raise CorpusValidationError(f"Trial-id leakage across splits: {sorted(overlap)}")
def validate_corpus(forms: list[LogicalForm], expected_version: str = SCHEMA_VERSION) -> None:
    """Run all single-corpus checks; raises on the first failure."""
    check_unique_ids(forms)
    check_schema_version(forms, expected_version)
`````
### FILE: criterialogic/tasks/__init__.py
`````python
"""Benchmark tasks A–D plus calibration, and shared item/prediction types."""
from criterialogic.tasks.base import Item, Prediction, expression_depth  # noqa: F401
`````
### FILE: criterialogic/tasks/base.py
`````python
"""Shared types for benchmark tasks: Item, Prediction, and a depth utility."""
from __future__ import annotations
from pydantic import BaseModel, Field
from criterialogic.oracle import PatientFacts
from criterialogic.schema.logical_form import Atom, BooleanGroup, Expression, LogicalForm, Not
class Item(BaseModel):
    """One evaluable unit. For matching/compositional: a (criterion, patient) pair."""
    item_id: str
    task: str  # "matching" | "compositional" | "structuring" | "typing_polarity"
    criterion: LogicalForm
    facts: PatientFacts
    gold: bool  # met (True) / not-met (False) under the oracle
    group: str | None = None  # criterion tag (matching) — for per-criterion breakdown
    depth: int | None = None  # logical nesting depth (compositional) — for depth stratification
class Prediction(BaseModel):
    """A model's output for one item: a met/not-met decision + a confidence in [0, 1]."""
    item_id: str
    label: bool
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    abstain: bool = False
    rationale: str | None = None
def expression_depth(expr: Expression) -> int:
    """Logical nesting depth: nested boolean groups. Atom=0, flat AND/OR=1, AND[...OR...]=2."""
    if isinstance(expr, Atom):
        return 0
    if isinstance(expr, Not):
        return expression_depth(expr.operand)
    if isinstance(expr, BooleanGroup):
        return 1 + max(expression_depth(op) for op in expr.operands)
    raise TypeError(f"Unknown node: {type(expr)!r}")
`````
### FILE: criterialogic/tasks/calibration.py
`````python
"""Cross-cutting calibration & abstention.
Reuses any task's predictions (which carry a confidence) and is scored by
metrics.calibration (ECE + selective accuracy). No separate item set is needed.
"""
TASK_NAME = "calibration"
`````
### FILE: criterialogic/tasks/compositional.py
`````python
"""Task D — compositional-logic stress test + its deterministic generator.
Atoms drawn from a pool (here, the leaf predicates of the n2c2 criteria) are
composed into nested AND/OR/NOT structures of controlled depth, with a known
ground-truth label (the oracle) under a sampled patient. Because generation is
seeded, the synthetic set is regenerable rather than a black box (spec §11).
"""
from __future__ import annotations
import random
from criterialogic.data.n2c2_criteria import n2c2_criteria_as_logical_forms
from criterialogic.data.synthetic import _collect_atoms, _sample_fact_for_atom
from criterialogic.oracle import Fact, PatientFacts, is_met
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Expression,
    LogicalForm,
    Not,
    Polarity,
    Source,
)
from criterialogic.tasks.base import Item, expression_depth
def _atom_pool() -> list[Atom]:
    pool: list[Atom] = []
    seen: set[str] = set()
    for form in n2c2_criteria_as_logical_forms():
        for atom in _collect_atoms(form.expression):
            key = atom.model_dump_json()
            if key not in seen:
                seen.add(key)
                pool.append(atom)
    return pool
def _build_expr(depth: int, pool: list[Atom], rng: random.Random) -> Expression:
    """Recursively build an expression of (at most) the requested nesting depth."""
    if depth <= 0:
        atom = rng.choice(pool)
        return Not(operand=atom) if rng.random() < 0.25 else atom
    op = rng.choice([BoolOp.AND, BoolOp.OR])
    k = rng.choice([2, 2, 3])
    operands = [_build_expr(depth - 1, pool, rng) for _ in range(k)]
    group: Expression = BooleanGroup(operator=op, operands=operands)
    return Not(operand=group) if rng.random() < 0.15 else group
def generate_compositional_items(
    n_per_depth: int = 12, max_depth: int = 3, seed: int = 29
) -> list[Item]:
    """Build Task-D items across nesting depths 1..max_depth."""
    rng = random.Random(seed)
    pool = _atom_pool()
    items: list[Item] = []
    for depth in range(1, max_depth + 1):
        for i in range(n_per_depth):
            expr = _build_expr(depth, pool, rng)
            form = LogicalForm(
                criterion_id=f"ctgov:synth:d{depth}:{i:03d}",
                source=Source.CTGOV_SYNTHETIC,
                polarity=Polarity.INCLUSION,
                text="(synthetic compositional criterion)",
                expression=expr,
                metadata={"synthetic": "true"},
            )
            # sample a patient over this expression's atoms
            facts: dict[str, Fact] = {}
            for atom in _collect_atoms(expr):
                f = _sample_fact_for_atom(atom, rng)
                if f is not None:
                    facts[atom.entity.text] = f
            patient = PatientFacts(record_id=f"synthD-{depth}-{i:03d}", facts=facts)
            items.append(Item(
                item_id=f"comp:d{depth}:{i:03d}",
                task="compositional",
                criterion=form,
                facts=patient,
                gold=is_met(form, patient),
                depth=expression_depth(expr),
            ))
    return items
`````
### FILE: criterialogic/tasks/matching.py
`````python
"""Task C — patient–criterion matching (met / not-met). Gold: n2c2 2018.
In the runnable demo the items are built by `data.synthetic.generate_matching_items`
over the public n2c2 criterion definitions with synthetic patients. With real
DUA-obtained n2c2 records, swap in `data.loaders.n2c2` as the item source; the
task contract (an `Item` with a `criterion`, `facts`, and gold `met`) is identical.
"""
from criterialogic.data.synthetic import generate_matching_items  # noqa: F401
TASK_NAME = "matching"
`````
### FILE: criterialogic/tasks/structuring.py
`````python
"""Task A — criteria structuring: free-text eligibility -> LogicalForm.
Gold: Chia. Scored with entity/relation F1 + logical-form exact match
(see metrics.extraction). Requires a parser/LLM that emits a LogicalForm; wired
here as a task name + contract. Not exercised by the zero-dependency demo.
"""
TASK_NAME = "structuring"
`````
### FILE: criterialogic/tasks/typing_polarity.py
`````python
"""Task B — criterion typing & polarity (entity type, inclusion/exclusion, qualifiers).
Gold derives from Chia (+ derived labels). Requires an extraction/classification
model; wired here as a task name + contract. Not exercised by the zero-dependency
demo (which uses already-structured forms).
"""
TASK_NAME = "typing_polarity"
`````
### FILE: criterialogic/taxonomy/__init__.py
`````python
"""Reasoning-failure taxonomy: the 7 categories + an error-annotation helper."""
from criterialogic.taxonomy.categories import CATEGORY_DESCRIPTIONS, FailureCategory  # noqa: F401
`````
### FILE: criterialogic/taxonomy/annotate.py
`````python
"""Heuristic error labelling for the demo's per-model failure breakdown.
IMPORTANT: this is a *heuristic aid* for error triage, not the released gold
taxonomy. The paper's taxonomy is produced by human annotation with reported
inter-annotator agreement (spec §6); these heuristics pre-sort errors to make
that human pass cheaper, and they drive the demo's illustrative breakdown.
The heuristics work by counterfactual probing on the structured form: if
*ignoring negation* would have fixed the error -> NEGATION_POLARITY; if the only
constraints involved are temporal/numeric -> TEMPORAL / NUMERIC_THRESHOLD; if a
compound (depth >= 1) is involved -> LOGICAL_COMPOSITION; else UNATTRIBUTED.
"""
from __future__ import annotations
from collections import Counter
from criterialogic.oracle import evaluate
from criterialogic.schema.logical_form import Atom, BooleanGroup, Expression, Not
from criterialogic.tasks.base import expression_depth
from criterialogic.taxonomy.categories import FailureCategory
def _has(expr: Expression, attr: str) -> bool:
    if isinstance(expr, Atom):
        return getattr(expr, attr) is not None
    if isinstance(expr, Not):
        return _has(expr.operand, attr)
    if isinstance(expr, BooleanGroup):
        return any(_has(op, attr) for op in expr.operands)
    return False
def _contains_not(expr: Expression) -> bool:
    if isinstance(expr, Not):
        return True
    if isinstance(expr, BooleanGroup):
        return any(_contains_not(op) for op in expr.operands)
    return False
def _strip_negation(expr: Expression) -> Expression:
    if isinstance(expr, Atom):
        return expr
    if isinstance(expr, Not):
        return _strip_negation(expr.operand)
    if isinstance(expr, BooleanGroup):
        return BooleanGroup(operator=expr.operator, operands=[_strip_negation(o) for o in expr.operands])
    raise TypeError(type(expr))
def categorize_error(item, prediction) -> FailureCategory:
    """Return a heuristic failure category for one (item, prediction)."""
    if prediction.label == item.gold:
        return FailureCategory.NONE
    expr = item.criterion.expression
    # Would ignoring negation have produced the model's (wrong) answer? -> negation flip
    if _contains_not(expr):
        stripped = evaluate(_strip_negation(expr), item.facts)
        if stripped is not None and bool(stripped) == prediction.label:
            return FailureCategory.NEGATION_POLARITY
    depth = expression_depth(expr)
    if depth >= 1:
        return FailureCategory.LOGICAL_COMPOSITION
    if _has(expr, "temporal") and not _has(expr, "numeric"):
        return FailureCategory.TEMPORAL
    if _has(expr, "numeric"):
        return FailureCategory.NUMERIC_THRESHOLD
    return FailureCategory.IMPLICIT_KNOWLEDGE
def failure_breakdown(items, predictions) -> dict[str, int]:
    """Counter of failure categories over the error set (correct items -> NONE excluded)."""
    pred_by_id = {p.item_id: p for p in predictions}
    counts = Counter(
        categorize_error(it, pred_by_id[it.item_id]).value
        for it in items
        if pred_by_id[it.item_id].label != it.gold
    )
    return dict(counts)
`````
### FILE: criterialogic/taxonomy/categories.py
`````python
"""The seven reasoning-failure categories (the paper's differentiator, spec §5)."""
from __future__ import annotations
from enum import Enum
class FailureCategory(str, Enum):
    NEGATION_POLARITY = "negation_polarity"      # exclusion treated as inclusion, or NOT dropped
    TEMPORAL = "temporal"                         # "within 6 months", "prior", "current", "ever"
    NUMERIC_THRESHOLD = "numeric_threshold"       # boundary / comparator mistakes
    LOGICAL_COMPOSITION = "logical_composition"   # wrong AND/OR/NOT scoping in compounds
    ENTITY_CONFLATION = "entity_conflation"       # clinically distinct entities confused
    IMPLICIT_KNOWLEDGE = "implicit_knowledge"     # unstated medical inference required
    FABRICATION = "fabrication"                   # invents a constraint not in the criterion
    NONE = "none"                                 # correct, or error not attributable
CATEGORY_DESCRIPTIONS = {
    FailureCategory.NEGATION_POLARITY: "Inclusion/exclusion or NOT-scope flipped.",
    FailureCategory.TEMPORAL: "Temporal window or tense reasoning error.",
    FailureCategory.NUMERIC_THRESHOLD: "Comparator or boundary value error.",
    FailureCategory.LOGICAL_COMPOSITION: "AND/OR/NOT composition resolved incorrectly.",
    FailureCategory.ENTITY_CONFLATION: "Distinct clinical entities conflated.",
    FailureCategory.IMPLICIT_KNOWLEDGE: "Failed required unstated inference.",
    FailureCategory.FABRICATION: "Asserted a constraint absent from the criterion.",
    FailureCategory.NONE: "No attributable failure.",
}
`````
### FILE: criterialogic/taxonomy/reliability.py
`````python
"""Reliability tooling for the reasoning-failure taxonomy (single-annotator workflow).
Operationalizes the paper's Section 5 procedure without a second annotator:
1. `export_error_set(items, predictions, path)` writes every misclassified item to a CSV
   with the rendered criterion, the patient facts, gold vs predicted, the automatic
   heuristic category, and a blank `human_category` column for the annotator to fill.
2. The domain-expert annotator fills `human_category` (in a spreadsheet), using the codebook.
3. `reliability_report(...)` computes:
     - human vs. automatic agreement (Cohen's κ + percent) — the independent cross-check;
     - test–retest agreement between two annotation passes — intra-annotator reliability.
All metrics are implemented from scratch (stdlib only).
"""
from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path
from criterialogic.models.llm_api import render_criterion, render_patient
from criterialogic.taxonomy.annotate import categorize_error
from criterialogic.taxonomy.categories import FailureCategory
CATEGORY_VALUES = [c.value for c in FailureCategory]
def cohens_kappa(a: list[str], b: list[str]) -> float:
    """Cohen's κ between two aligned lists of categorical labels."""
    if len(a) != len(b):
        raise ValueError("label lists must be the same length")
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    cats = set(a) | set(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if pe >= 1.0:  # both raters used a single identical category throughout
        return 1.0
    return (po - pe) / (1 - pe)
def percent_agreement(a: list[str], b: list[str]) -> float:
    if len(a) != len(b):
        raise ValueError("label lists must be the same length")
    return sum(1 for x, y in zip(a, b) if x == y) / len(a) if a else 0.0
def _error_rows(items, predictions):
    pred = {p.item_id: p for p in predictions}
    for it in items:
        p = pred[it.item_id]
        if p.label != it.gold:  # errors only
            yield it, p, categorize_error(it, p).value
def export_error_set(items, predictions, path: str) -> dict:
    """Write the error set to a CSV for human annotation. Returns a small summary."""
    rows = list(_error_rows(items, predictions))
    fields = ["item_id", "task", "criterion", "patient_facts", "gold", "predicted",
              "confidence", "automatic_category", "human_category"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for it, p, auto in rows:
            w.writerow({
                "item_id": it.item_id,
                "task": it.task,
                "criterion": render_criterion(it.criterion),
                "patient_facts": render_patient(it.facts).replace("\n", " | "),
                "gold": "met" if it.gold else "not_met",
                "predicted": "met" if p.label else "not_met",
                "confidence": f"{p.confidence:.3f}",
                "automatic_category": auto,
                "human_category": "",  # annotator fills this using the codebook
            })
    return {"path": path, "n_errors": len(rows), "categories": CATEGORY_VALUES}
def load_labels(path: str, column: str = "human_category") -> dict[str, str]:
    """Read {item_id: label} from an annotated CSV (skips blank labels)."""
    out: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            val = (row.get(column) or "").strip()
            if val:
                out[row["item_id"]] = val
    return out
def human_vs_automatic(items, predictions, human_labels: dict[str, str]) -> dict:
    """Agreement between the human labels and the automatic heuristic labeler."""
    auto = {it.item_id: cat for it, _, cat in _error_rows(items, predictions)}
    ids = [i for i in human_labels if i in auto]
    h = [human_labels[i] for i in ids]
    a = [auto[i] for i in ids]
    return {
        "n": len(ids),
        "cohens_kappa": round(cohens_kappa(h, a), 4),
        "percent_agreement": round(percent_agreement(h, a), 4),
        "human_distribution": dict(Counter(h)),
        "automatic_distribution": dict(Counter(a)),
    }
def test_retest(labels_pass1: dict[str, str], labels_pass2: dict[str, str]) -> dict:
    """Intra-annotator agreement between two labeling passes over the shared items."""
    ids = [i for i in labels_pass1 if i in labels_pass2]
    a = [labels_pass1[i] for i in ids]
    b = [labels_pass2[i] for i in ids]
    return {
        "n": len(ids),
        "cohens_kappa": round(cohens_kappa(a, b), 4),
        "percent_agreement": round(percent_agreement(a, b), 4),
    }
def reliability_report(items, predictions, human_csv: str, retest_csv: str | None = None) -> dict:
    """Convenience: human-vs-automatic (+ optional test–retest) from annotated CSV(s)."""
    human = load_labels(human_csv)
    report = {"human_vs_automatic": human_vs_automatic(items, predictions, human)}
    if retest_csv:
        report["test_retest"] = test_retest(human, load_labels(retest_csv))
    return report
`````
### FILE: data/README.md
`````markdown
# Data
`data/raw/` and `data/processed/` are **gitignored**. Nothing here is committed.
## Chia (releasable, CC-BY)
- figshare: https://doi.org/10.6084/m9.figshare.11855817
- Hugging Face: https://huggingface.co/datasets/bigbio/chia
- Place `.txt`/`.ann` under `data/raw/chia/`; load via `criterialogic.data.loaders.chia`.
## ClinicalTrials.gov (public)
- Fetched at runtime by `criterialogic.data.loaders.ctgov` (API v2). No download needed.
## n2c2 2018 Track 1 — Cohort Selection (DUA-GATED, NOT redistributable)
- Request access: https://n2c2.dbmi.hms.harvard.edu/
- After approval, place patient XML under `data/raw/n2c2_2018/`.
- The 13 criterion **definitions** are public and live in code
  (`criterialogic.data.n2c2_criteria`); only the patient records are restricted.
- We **never** commit or redistribute n2c2 records — only this pointer + the harness.
`````
### FILE: data/raw/.gitkeep
`````text
`````
### FILE: docs/index.md
`````markdown
# CriteriaLogic — docs
## Repository layout
```
criterialogic/
  schema/logical_form.py   # the harmonized logical form (pydantic v2)
  schema/validators.py     # corpus-level checks
  oracle.py                # three-valued evaluator (ground truth + rule-based engine)
  data/
    n2c2_criteria.py       # 13 public n2c2 criteria as LogicalForms
    synthetic.py           # seeded synthetic patient-fact generator
    loaders/{chia,n2c2,ctgov}.py
    harmonize.py, splits.py
  tasks/                   # A–D + calibration; base Item/Prediction
  models/                  # Model interface + rule_based, negation_blind, + LLM/encoder stubs
  metrics/                 # classification, matching (n2c2), logic-by-depth, calibration, extraction
  taxonomy/                # 7 failure categories + heuristic labeler
  eval/                    # runner + markdown report
  leaderboard/             # submit + score
scripts/                   # run_eval, build_logic_set, make_demo_data, download_data
```
## Leaderboard hosting
A Hugging Face Space or this `docs/` site renders the scored submissions.
`````
### FILE: scripts/build_logic_set.py
`````python
#!/usr/bin/env python3
"""Generate the Task-D compositional-logic stress-test deterministically and save it.
    python scripts/build_logic_set.py --n-per-depth 20 --max-depth 4 --seed 29 --out data/processed/logic_set.json
Reproducible: same seed -> identical set (spec §11).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from criterialogic.tasks.compositional import generate_compositional_items
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-depth", type=int, default=20)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--out", default="data/processed/logic_set.json")
    args = ap.parse_args()
    items = generate_compositional_items(args.n_per_depth, args.max_depth, args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps([it.model_dump() for it in items], indent=2, default=str))
    print(f"[wrote] {args.out}  ({len(items)} items, depths 1..{args.max_depth}, seed={args.seed})")
if __name__ == "__main__":
    main()
`````
### FILE: scripts/download_data.py
`````python
#!/usr/bin/env python3
"""Pull the data CriteriaLogic needs.
Releasable sources are fetched; the DUA-gated one is only located, never downloaded.
    python scripts/download_data.py --all                 # Chia + a default ctgov cache, + n2c2 status
    python scripts/download_data.py --chia                 # download + extract Chia (brat .txt/.ann) from figshare
    python scripts/download_data.py --chia --hf            # alternative Chia route via Hugging Face (needs `datasets`)
    python scripts/download_data.py --ctgov "type 2 diabetes" --n 100   # cache ClinicalTrials.gov eligibility text
    python scripts/download_data.py --status               # show what is present locally (incl. n2c2 DUA status)
n2c2 2018 is DUA-gated: this tool never downloads it. Obtain it from the Harvard DBMI
portal and place the patient XML under data/raw/n2c2_2018/ (gitignored).
"""
from __future__ import annotations
import argparse
import json
import sys
from criterialogic.data import download as dl
def main() -> None:
    ap = argparse.ArgumentParser(description="Pull CriteriaLogic data (releasable sources only).")
    ap.add_argument("--all", action="store_true", help="Chia + default ctgov cache + n2c2 status.")
    ap.add_argument("--chia", action="store_true", help="Download + extract Chia (CC-BY) from figshare.")
    ap.add_argument("--hf", action="store_true", help="Use the Hugging Face Chia route (needs `datasets`).")
    ap.add_argument("--force", action="store_true", help="Re-download Chia even if already present.")
    ap.add_argument("--ctgov", metavar="QUERY", nargs="?", const="type 2 diabetes",
                    help="Cache ClinicalTrials.gov eligibility text for QUERY.")
    ap.add_argument("--n", type=int, default=50, help="Number of trials for --ctgov (default 50).")
    ap.add_argument("--status", action="store_true", help="Report what is present locally; downloads nothing.")
    args = ap.parse_args()
    if not any([args.all, args.chia, args.ctgov is not None, args.status]):
        ap.print_help()
        return
    def show(d: dict) -> None:
        print(json.dumps(d, indent=2))
    try:
        if args.status:
            show(dl.verify())
            return
        if args.chia or args.all:
            if args.hf:
                show(dl.download_chia_hf())
            else:
                show(dl.download_chia_figshare(force=args.force))
        if args.ctgov is not None or args.all:
            query = args.ctgov if args.ctgov is not None else "type 2 diabetes"
            show(dl.cache_ctgov_criteria(query=query, n=args.n))
        if args.all:
            print("\nn2c2 2018 (DUA-gated — not downloaded):")
            show(dl.n2c2_status())
    except dl.DownloadError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
if __name__ == "__main__":
    main()
`````
### FILE: scripts/make_demo_data.py
`````python
#!/usr/bin/env python3
"""Materialise the synthetic demo datasets to disk (matching + compositional)."""
from __future__ import annotations
import json
from pathlib import Path
from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.tasks.compositional import generate_compositional_items
def main() -> None:
    out = Path("data/processed")
    out.mkdir(parents=True, exist_ok=True)
    match = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=8, seed=13)
    comp = generate_compositional_items(n_per_depth=12, max_depth=3, seed=29)
    (out / "matching_demo.json").write_text(json.dumps([i.model_dump() for i in match], indent=2, default=str))
    (out / "compositional_demo.json").write_text(json.dumps([i.model_dump() for i in comp], indent=2, default=str))
    print(f"[wrote] {out}/matching_demo.json ({len(match)} items)")
    print(f"[wrote] {out}/compositional_demo.json ({len(comp)} items)")
if __name__ == "__main__":
    main()
`````
### FILE: scripts/run_eval.py
`````python
#!/usr/bin/env python3
"""Thin wrapper so `python scripts/run_eval.py` works from a clone.
The implementation lives in `criterialogic.cli` (inside the installed package) so
that the `criterialogic-eval` console script also resolves after `pip install`.
"""
from criterialogic.cli import main
if __name__ == "__main__":
    main()
`````
### FILE: tests/test_download.py
`````python
"""Tests for the data-acquisition helpers (network-free parts only)."""
import zipfile
from criterialogic.data import download as dl
from criterialogic.data.loaders.chia import load_chia_dir
def test_n2c2_status_absent(tmp_path):
    st = dl.n2c2_status(tmp_path / "n2c2_2018")
    assert st["present"] is False
    assert st["n_files"] == 0
    assert "n2c2.dbmi.hms.harvard.edu" in st["portal"]
def test_extract_and_parse_chia_brat(tmp_path):
    # Simulate the figshare archive layout (nested subfolder) and the loader's recursive read.
    zpath = tmp_path / "Chia_w_scope.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("Chia_w_scope/NCT00000001.ann",
                    "T1\tCondition 0 14\ttype 2 diabetes\nT2\tDrug 19 26\taspirin\n")
        zf.writestr("Chia_w_scope/NCT00000001.txt", "type 2 diabetes and aspirin\n")
    dest = tmp_path / "chia"
    assert dl._extract_archives([zpath], dest) == 1
    forms = load_chia_dir(str(dest))
    assert len(forms) == 2
    assert all(f.source.value == "chia" for f in forms)
def test_chia_idempotent_skip(tmp_path):
    dest = tmp_path / "chia"
    dest.mkdir()
    (dest / "x.ann").write_text("T1\tCondition 0 4\ttest\n")
    assert dl.download_chia_figshare(dest=dest)["status"] == "already_present"
def test_verify_summary(tmp_path):
    summary = dl.verify(tmp_path)
    assert summary["chia_ann_files"] == 0
    assert summary["ctgov_cached_queries"] == 0
    assert summary["n2c2"]["present"] is False
`````
### FILE: tests/test_end_to_end.py
`````python
"""End-to-end: the demo pipeline runs and the diagnostics behave as designed."""
from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.eval.runner import run_task
from criterialogic.models import NegationBlindModel, RuleBasedModel
from criterialogic.tasks.compositional import generate_compositional_items
def test_thirteen_criteria():
    assert len(harmonized_n2c2_criteria()) == 13
def test_matching_pipeline_runs():
    items = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=6, seed=13)
    res = run_task(RuleBasedModel(), items, seed=13)
    assert res["task"] == "matching"
    # rule-based == oracle on structured input -> perfect by construction
    assert res["metrics"]["overall_micro_f1"] == 1.0
    assert res["failure_taxonomy"] == {}
def test_compositional_depth_and_taxonomy():
    items = generate_compositional_items(n_per_depth=10, max_depth=3, seed=29)
    res = run_task(NegationBlindModel(), items, seed=29)
    assert res["task"] == "compositional"
    # the negation-blind model should make attributable errors (taxonomy non-empty)
    assert sum(res["failure_taxonomy"].values()) > 0
    assert set(res["metrics"]["by_depth"]) == {1, 2, 3}
def test_determinism():
    a = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=5, seed=99)
    b = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=5, seed=99)
    assert [i.gold for i in a] == [i.gold for i in b]
`````
### FILE: tests/test_leaderboard.py
`````python
"""Leaderboard submission validation + scoring round-trip."""
import json
from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.leaderboard.score import score_submission
from criterialogic.leaderboard.submit import load_submission, validate_against_items
from criterialogic.models import RuleBasedModel
def test_submission_round_trip(tmp_path):
    items = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=4, seed=1)
    preds = RuleBasedModel().predict_batch(items)
    sub = {"model": "rule_based", "task": "matching",
           "predictions": [p.model_dump() for p in preds]}
    path = tmp_path / "submission.json"
    path.write_text(json.dumps(sub))
    loaded = load_submission(str(path))
    validate_against_items(loaded, items)  # should not raise
    scored = score_submission(loaded, items)
    assert scored["metrics"]["overall_micro_f1"] == 1.0
`````
### FILE: tests/test_llm_api.py
`````python
"""OpenAI adapter: rendering + parsing + graceful failure, with the API call mocked."""
from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.models.llm_api import OpenAILLMModel, render_expression
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Entity,
    EntityType,
    Not,
)
class _Fake(OpenAILLMModel):
    """OpenAI adapter with the network call replaced by a canned response (or exception)."""
    def __init__(self, canned, **kw):
        super().__init__(cache_dir=None, **kw)  # no disk cache in tests
        self._canned = canned
    def _complete(self, system, user):
        if isinstance(self._canned, Exception):
            raise self._canned
        return self._canned
def _an_item():
    return generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=1, seed=1)[0]
def test_parses_clean_json():
    m = _Fake('{"label": true, "confidence": 0.9, "rationale": "meets"}')
    p = m.predict(_an_item())
    assert p.label is True and abs(p.confidence - 0.9) < 1e-9 and p.rationale == "meets"
def test_strips_code_fence_and_clamps_confidence():
    m = _Fake('```json\n{"label": false, "confidence": 1.5}\n```')
    p = m.predict(_an_item())
    assert p.label is False and p.confidence == 1.0  # clamped into [0,1]
def test_graceful_failure_abstains():
    m = _Fake(RuntimeError("boom"), max_retries=0)
    p = m.predict(_an_item())
    assert p.abstain is True and p.confidence == 0.0 and "boom" in p.rationale
def test_render_expression_is_faithful():
    a = Atom(entity=Entity(text="t2dm", type=EntityType.CONDITION))
    b = Atom(entity=Entity(text="aspirin", type=EntityType.DRUG))
    expr = BooleanGroup(operator=BoolOp.AND, operands=[a, Not(operand=b)])
    s = render_expression(expr)
    assert "AND" in s and "NOT" in s and "t2dm" in s and "aspirin" in s
def test_info_reports_model():
    m = _Fake("{}", model="gpt-4o-mini")
    assert m.info()["provider"] == "openai" and m.info()["model"] == "gpt-4o-mini"
import types  # noqa: E402
def test_string_and_numeric_label_coercion():
    assert _Fake('{"label": "false", "confidence": 0.8}').predict(_an_item()).label is False
    assert _Fake('{"label": "met", "confidence": 0.8}').predict(_an_item()).label is True
    assert _Fake('{"label": 1, "confidence": 0.8}').predict(_an_item()).label is True
    # an uninterpretable label must abstain, not silently guess
    assert _Fake('{"label": "maybe", "confidence": 0.8}').predict(_an_item()).abstain is True
class _TempRejectingClient:
    """Fake OpenAI client: rejects a custom temperature, succeeds without one."""
    def __init__(self):
        self.n_calls = 0
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create))
    def _create(self, **kwargs):
        self.n_calls += 1
        if "temperature" in kwargs:
            raise RuntimeError("Unsupported value: 'temperature' is not supported with this model.")
        msg = types.SimpleNamespace(content='{"label": true, "confidence": 0.6}')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
def test_temperature_rejection_fallback():
    c = _TempRejectingClient()
    m = OpenAILLMModel(client=c, cache_dir=None, max_retries=0)
    p = m.predict(_an_item())
    assert p.abstain is False and p.label is True          # succeeded via fallback
    assert m.temperature is None and c.n_calls == 2        # retried once without temperature
`````
### FILE: tests/test_metrics.py
`````python
"""Metric correctness on tiny hand-computed cases."""
from criterialogic.metrics.classification import accuracy, macro_f1, micro_f1, per_class_prf
def test_perfect_scores():
    y = [True, False, True, False]
    assert micro_f1(y, y) == 1.0
    assert macro_f1(y, y) == 1.0
    assert accuracy(y, y) == 1.0
def test_micro_f1_equals_accuracy_single_label():
    # For single-label data, micro-F1 == accuracy. Only item 0 is correct -> 1/3.
    yt = [True, True, False]
    yp = [True, False, True]
    assert abs(micro_f1(yt, yp) - 1 / 3) < 1e-9
    assert abs(accuracy(yt, yp) - 1 / 3) < 1e-9
def test_per_class_positive_f1():
    # Positive ("True") class: 1 TP, 1 FP, 1 FN -> P=R=F1=0.5
    yt = [True, True, False]
    yp = [True, False, True]
    assert abs(per_class_prf(yt, yp)[True]["f1"] - 0.5) < 1e-9
`````
### FILE: tests/test_oracle.py
`````python
"""Three-valued evaluator semantics."""
from criterialogic.oracle import Fact, PatientFacts, evaluate, is_met
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Entity,
    EntityType,
    Not,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
)
def test_numeric_between_boundaries():
    atom = Atom(entity=Entity(text="HbA1c", type=EntityType.MEASUREMENT),
                numeric=NumericConstraint(operator=Comparator.BETWEEN, value=6.5, upper=9.5, unit="%"))
    facts_in = PatientFacts(record_id="p", facts={"HbA1c": Fact(value=7.2)})
    facts_out = PatientFacts(record_id="p", facts={"HbA1c": Fact(value=10.0)})
    assert evaluate(atom, facts_in) is True
    assert evaluate(atom, facts_out) is False
def test_temporal_window():
    atom = Atom(entity=Entity(text="mi", type=EntityType.CONDITION),
                temporal=TemporalConstraint(operator=TemporalOp.WITHIN, value=6, unit=TimeUnit.MONTHS))
    recent = PatientFacts(record_id="p", facts={"mi": Fact(present=True, days_ago=60)})
    old = PatientFacts(record_id="p", facts={"mi": Fact(present=True, days_ago=400)})
    assert evaluate(atom, recent) is True
    assert evaluate(atom, old) is False
def test_unknown_propagates():
    atom = Atom(entity=Entity(text="HbA1c", type=EntityType.MEASUREMENT),
                numeric=NumericConstraint(operator=Comparator.GT, value=7.0))
    empty = PatientFacts(record_id="p", facts={})
    assert evaluate(atom, empty) is None  # absent measurement -> unknown
    assert is_met(_form(atom), empty) is False  # unknown collapses to not-met by default
def test_negation_and_or():
    a = Atom(entity=Entity(text="a", type=EntityType.CONDITION))
    b = Atom(entity=Entity(text="b", type=EntityType.CONDITION))
    facts = PatientFacts(record_id="p", facts={"a": Fact(present=True), "b": Fact(present=False)})
    assert evaluate(Not(operand=a), facts) is False
    assert evaluate(BooleanGroup(operator=BoolOp.OR, operands=[a, b]), facts) is True
    assert evaluate(BooleanGroup(operator=BoolOp.AND, operands=[a, b]), facts) is False
def _form(expr):
    from criterialogic.schema.logical_form import LogicalForm, Polarity, Source
    return LogicalForm(criterion_id="t:1", source=Source.CTGOV_SYNTHETIC,
                       polarity=Polarity.INCLUSION, text="t", expression=expr)
`````
### FILE: tests/test_reliability.py
`````python
"""Taxonomy reliability metrics + annotation CSV round-trip."""
import csv
from criterialogic.models import NegationBlindModel
from criterialogic.tasks.compositional import generate_compositional_items
from criterialogic.taxonomy.reliability import (
    cohens_kappa,
    export_error_set,
    human_vs_automatic,
    load_labels,
    percent_agreement,
)
from criterialogic.taxonomy.reliability import (
    test_retest as intra_retest,
)
def test_cohens_kappa_known_values():
    assert abs(cohens_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"])) < 1e-9  # chance-level -> 0
    assert cohens_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0                 # perfect -> 1
    assert abs(percent_agreement(["a", "a", "b"], ["a", "b", "b"]) - 2 / 3) < 1e-9
def _errors():
    items = generate_compositional_items(n_per_depth=8, max_depth=3, seed=29)
    preds = NegationBlindModel().predict_batch(items)
    return items, preds
def test_export_and_load_roundtrip(tmp_path):
    items, preds = _errors()
    out = tmp_path / "errors.csv"
    summary = export_error_set(items, preds, str(out))
    assert summary["n_errors"] > 0 and out.exists()
    assert load_labels(str(out)) == {}  # blank human_category on export
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    for r in rows:  # simulate a perfect human pass
        r["human_category"] = r["automatic_category"]
    annotated = tmp_path / "annotated.csv"
    with open(annotated, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    hv = human_vs_automatic(items, preds, load_labels(str(annotated)))
    assert hv["n"] == summary["n_errors"] and hv["cohens_kappa"] == 1.0
def test_test_retest_identical_passes():
    labels = {"comp:d1:000": "temporal", "comp:d2:001": "logical_composition"}
    tr = intra_retest(labels, {**labels})
    assert tr["cohens_kappa"] == 1.0 and tr["n"] == 2
`````
### FILE: tests/test_schema.py
`````python
"""Schema: round-trip, canonicalization, and structural validators."""
import pytest
from pydantic import ValidationError
from criterialogic.schema.logical_form import (
    Atom,
    BooleanGroup,
    BoolOp,
    Comparator,
    Entity,
    EntityType,
    LogicalForm,
    Not,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
    canonicalize,
    example_nested_compound,
    example_simple_inclusion,
)
def test_round_trip_identical():
    for lf in (example_simple_inclusion(), example_nested_compound()):
        blob = lf.model_dump_json()
        assert LogicalForm.model_validate_json(blob).model_dump_json() == blob
def test_canonicalize_idempotent_and_commutative():
    a = Atom(entity=Entity(text="a", type=EntityType.CONDITION))
    b = Atom(entity=Entity(text="b", type=EntityType.CONDITION))
    g1 = BooleanGroup(operator=BoolOp.AND, operands=[a, b])
    g2 = BooleanGroup(operator=BoolOp.AND, operands=[b, a])
    assert canonicalize(g1).model_dump_json() == canonicalize(g2).model_dump_json()
    c = example_nested_compound().canonical()
    assert c.canonical().model_dump_json() == c.model_dump_json()
def test_double_negation_collapses():
    a = Atom(entity=Entity(text="x", type=EntityType.CONDITION))
    assert isinstance(canonicalize(Not(operand=Not(operand=a))), Atom)
def test_between_requires_upper():
    with pytest.raises((ValidationError, ValueError)):
        NumericConstraint(operator=Comparator.BETWEEN, value=6.5)
def test_numeric_only_on_measurable_entity():
    with pytest.raises((ValidationError, ValueError)):
        Atom(entity=Entity(text="dka", type=EntityType.CONDITION),
             numeric=NumericConstraint(operator=Comparator.GT, value=1))
def test_group_needs_two_operands():
    with pytest.raises((ValidationError, ValueError)):
        BooleanGroup(operator=BoolOp.AND,
                     operands=[Atom(entity=Entity(text="x", type=EntityType.CONDITION))])
def test_windowed_temporal_requires_value_unit():
    with pytest.raises((ValidationError, ValueError)):
        TemporalConstraint(operator=TemporalOp.WITHIN)
`````
</user_query>