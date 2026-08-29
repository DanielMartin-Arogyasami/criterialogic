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
