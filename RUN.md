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
    # Task D atom pool — already committed; rebuild only to refresh or re-date it:
    python scripts/fetch_ctgov_atoms.py --limit 300 --first-posted-from 2026-01-01
    python scripts/fetch_ctgov_atoms.py --offline    # rebuild from the cache, no network
    # n2c2 is DUA-gated: request at https://n2c2.dbmi.hms.harvard.edu/ , place XML in data/raw/n2c2_2018/
## 6. Bigger compositional set (tighter estimates)
    python scripts/build_logic_set.py --n-per-depth 100 --max-depth 4 --seed 29 --out data/processed/logic_set.json
