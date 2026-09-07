# Contributing / leaderboard submissions

## Submit a model

1. Subclass `criterialogic.models.base.Model` and implement
   `predict(item) -> Prediction`. That is the whole interface. `predict_batch` is
   provided and worth overriding if your calls can run concurrently.
2. Build the item set and produce a submission:
   ```bash
   python scripts/make_submission.py --task compositional --model <name> --out sub.json
   ```
   A submission is JSON:
   ```json
   {"model": "<name>", "task": "compositional",
    "predictions": [{"item_id": "comp:d2:000", "label": true, "confidence": 0.83}]}
   ```
3. Validate and score with the same runner the reported results used:
   ```bash
   python scripts/make_submission.py --task compositional --score sub.json
   ```
   Validation fails loudly on a missing or unknown `item_id`, so a submission cannot be
   scored against a partly different item set.
4. Report the model identifier, inference parameters, and seeds — the fields
   `Model.info()` returns. If your model refuses a parameter you requested, report what
   was applied, not what was asked for.
5. Open a PR adding your result JSON under `results/leaderboard/` and your row to the
   README table, with the Wilson interval alongside the point estimate.

## Confidence is not optional

Every prediction carries a confidence, and the calibration layer is scored across every
arm. A model that returns a constant confidence is flagged as having no usable
abstention signal, and its selective-accuracy curve is reported as flat rather than as a
curve. If your system has no meaningful confidence, say so in the PR — it is a fair
result, and preferable to a constant that gets read as calibration.

## Code

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```

- Public-domain and synthetic data only. Never commit anything under `data/raw/`.
- `criterialogic/metrics/stats.py` is standard-library only and must stay that way, so
  the arithmetic behind every reported interval can be executed without installing
  anything.
- If a change makes the code disagree with a claim in the manuscript, add an entry to
  `results/DISCREPANCIES.md` rather than editing the claim. Code changes do not rewrite
  scientific claims; the discrepancy is recorded and the author decides the wording.
- Do not add a number to any results file that was not produced by executing code.
