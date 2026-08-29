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
