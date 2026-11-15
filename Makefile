# CriteriaLogic — the whole remaining project, as commands.
#
# Everything except `run-llm` and the annotation pass is deterministic: no API key, no
# network, no model calls, no assistant tokens. Run `make finish` and read the output.

PY ?= python
RESULTS ?= results
MODEL ?= openai
NPD ?= 60
ifeq ($(OS),Windows_NT)
VENV_PY = .venv/Scripts/python.exe
else
VENV_PY = .venv/bin/python
endif

.PHONY: help setup check data run-offline run-llm paper supplement verify verify-paper annotate-export annotate-report finish release clean revision run-size-matched run-size-sweep

help:
	@echo "CriteriaLogic — make targets (in the order you need them)"
	@echo ""
	@echo "  setup            venv + editable install (corporate: set PIP_INDEX_URL first)"
	@echo "  check            preflight + pytest + ruff   <- run this first, it is the moment of truth"
	@echo "  data             Arm 1 counts + Arm 2 item set   <- fills the Section 3 brackets"
	@echo "  run-offline      both arms, diagnostic models, no key"
	@echo "  run-llm          depth sweep + Arm 1 under prompt v2 (MODEL=, NPD=)  <- needs a key"
	@echo "  paper            regenerate results/paper_data.md"
	@echo "  supplement       assemble S1, S3–S5 into supplement/ from repo files"
	@echo "  verify           diff the numbers extract against the artifacts (exits non-zero on drift)"
	@echo "  verify-paper     same check against paper/CriteriaLogic.md (local; the manuscript is gitignored)"
	@echo "  annotate-export  draw the sample, write the two blind annotator files"
	@echo "  annotate-report  kappa + adjudication sheet"
	@echo "  finish           setup -> check -> data -> run-offline -> paper -> verify"
	@echo "  revision         per-depth structure, Arm 1 re-score, size-matched offline check (no key)"
	@echo "  run-size-matched size-matched set on gpt-4o-mini, prompt v2   <- needs a key"
	@echo "  run-size-sweep   fixed-depth size sweep on gpt-4o-mini, prompt v2   <- needs a key"
	@echo "  release          pre-release gate: clean tree, tests, verify, no placeholders"

setup:
	$(PY) -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -e ".[dev]"
	@echo "Now use:  make check PY=$(VENV_PY)"

check:
	$(PY) scripts/preflight.py
	$(PY) -m pytest -q
	$(PY) -m ruff check .

data:
	$(PY) scripts/build_real_criteria.py --stats
	$(PY) scripts/build_logic_set.py --depths 2,3,4,5,6 --n-per-depth 60 --seed 29 \
		--out data/processed/logic_set_depth_sweep.json

run-offline:
	$(PY) scripts/run_eval.py --outdir $(RESULTS)

# Requires OPENAI_API_KEY. Prompt v2 is the default and fixes both the currency-rendering
# defect and the exclusion-polarity ambiguity, so these numbers supersede the v0.2 ones.
run-llm:
	@test -n "$$OPENAI_API_KEY" || (echo "OPENAI_API_KEY is not set." && exit 1)
	$(PY) scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth $(NPD) --model $(MODEL) --outdir $(RESULTS)
	$(PY) scripts/run_eval.py --task real_criteria --model $(MODEL) --outdir $(RESULTS)

paper:
	$(PY) scripts/collect_paper_data.py --results $(RESULTS)

supplement:
	$(PY) scripts/assemble_supplement.py

verify:
	$(PY) scripts/collect_paper_data.py --verify --results $(RESULTS)

verify-paper:
	$(PY) scripts/collect_paper_data.py --verify --results $(RESULTS) \
	  --paper paper/CriteriaLogic.md

annotate-export:
	$(PY) scripts/annotation_export.py --results $(RESULTS) --prompt-version 2 \
	  --depths 2,3,4,5,6 --n-per-depth $(NPD) --n 200 --out annotation/

annotate-report:
	$(PY) scripts/annotation_report.py --a annotation/errors_annotator1.csv \
	  --b annotation/errors_annotator2.csv \
	  --adjudication-out annotation/adjudication.csv

finish: check data run-offline paper verify
	@echo ""
	@echo "Deterministic work complete. Read results/paper_data.md."
	@echo "Remaining, in order:  make run-llm   ->   make paper verify   ->   annotation"

# Pre-release gate. Fails loudly rather than letting a placeholder reach a preprint.
# Also fails on the stale handle `darogyasami`, which the placeholder was once filled with.
# paper/ is gitignored and may be absent; $(wildcard) keeps grep from erroring on it, since
# an error exit would make the negated check pass without looking at anything.
release: check verify
	@! grep -rnI --exclude-dir=__pycache__ 'GITHUB-HANDLE\|\[email\]\|darogyasami' \
	  $(wildcard paper/) README.md CITATION.cff pyproject.toml criterialogic/ \
	  || (echo 'Unfilled or stale placeholder above.' && exit 1)
	@echo "Release gate passed."

clean:
	rm -rf .venv **/__pycache__ .criterialogic_cache

# --- Revision R1: reviewer-requested analyses ------------------------------------------
revision:
	$(PY) scripts/depth_structure.py
	$(PY) scripts/rescore_real_criteria.py
	$(PY) scripts/run_size_matched.py
	$(PY) scripts/run_size_sweep.py

run-size-matched:
	$(PY) scripts/run_size_matched.py --model $(MODEL)

run-size-sweep:
	$(PY) scripts/run_size_sweep.py --model $(MODEL)
