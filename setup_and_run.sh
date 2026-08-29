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
