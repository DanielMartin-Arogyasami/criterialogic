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
