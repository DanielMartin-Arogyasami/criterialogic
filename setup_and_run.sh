#!/usr/bin/env bash
# Set up and smoke-test CriteriaLogic. No network, no API key.
set -euo pipefail

python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

echo
echo "== Arm 1: segmentation yield from the committed snapshot =="
python scripts/build_real_criteria.py --stats

echo
echo "== Both arms, offline diagnostics =="
python scripts/run_eval.py --limit 40 --n-per-depth 8 --max-depth 3

echo
echo "== Tests and lint =="
pytest -q
ruff check .

echo
echo "Done. Real model results need an API key — see RUN.md section 3."
