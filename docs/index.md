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
