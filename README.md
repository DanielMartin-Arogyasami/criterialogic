# CriteriaLogic

**A depth-parameterised stress test for logical reasoning over clinical-trial eligibility criteria.**

Eligibility criteria nest AND/OR, negate, bound values, and scope things in time. A
screening system can score well on average and still fail on the constructions where a
wrong answer flips an eligibility decision. CriteriaLogic makes logical nesting depth an
independent variable you can turn, with ground truth computed by a three-valued
evaluator rather than annotated, so a drop in accuracy is attributable to structure
rather than to vocabulary, topic, or prompt design.

Two arms, one snapshot, no gated data:

- **Arm 1 — real criteria.** Criteria segmented verbatim from a dated ClinicalTrials.gov
  API v2 snapshot, carrying real inclusion/exclusion polarity.
- **Arm 2 — compositional stress test.** Nested AND/OR/NOT expressions at controlled
  depths 1–6, composed from atoms extracted from the same snapshot.
- **Cross-cutting:** calibration and abstention (ECE, tie-aware selective accuracy).

Plus a seven-category reasoning-failure taxonomy and a published codebook. Human
annotation of the error set has not been run; the protocol is in `docs/CODEBOOK.md`.

> **Data policy:** public-domain and synthetic only. Everything needed to reproduce both
> arms is committed. No data-use agreement, no credentials.

> **Reproducing the results?** `RUN.md` has the turnkey commands, and `make finish` runs
> the whole deterministic chain. Remaining work is five cards in `docs/TASKS.md`.

## Quickstart

```bash
git clone https://github.com/DanielMartin-Arogyasami/criterialogic.git
cd criterialogic
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .

# Does this installation work? No network, no API key:
python scripts/preflight.py

# Runs both arms end-to-end with no network and no API key:
python scripts/run_eval.py
```

`preflight.py` checks the interpreter, the dependency, the resolved data directory, the
snapshot and the atom pool, then runs a real evaluation through both arms. Its exit code is
the number of failed checks.

That evaluates two offline diagnostics and writes JSON plus a Markdown report to
`results/`.

> **On those two diagnostics.** `rule_based` evaluates the already-structured logical
> form, so on these item sets it *is* the oracle and scores perfectly by construction —
> a software-validation artifact, not a finding. `negation_blind` is deliberately broken
> to produce a known error signature. Neither belongs on the leaderboard, and neither
> emits a varying confidence, so neither has an abstention curve worth reading.

## Real results

```bash
pip install -e ".[llm]"
export OPENAI_API_KEY=sk-...
export CRITERIALOGIC_LLM_MODEL=gpt-4o-mini    # or any chat model you can reach

# the depth sweep — this is the arm that carries the finding
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model openai

# the realism check
python scripts/run_eval.py --task real_criteria --model openai

# second and third systems — same prompt, OpenAI-compatible hosts
# pip install -e ".[llm]"
# $env:OPENROUTER_API_KEY="..."   # or TOGETHER_API_KEY
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model openrouter
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model together
```

Responses are cached under `.criterialogic_cache/`, keyed by model, prompt version, and
the parameters the API actually applied, so re-runs are free, interrupted runs resume,
and a parameter change invalidates the cache rather than silently reusing it.

## Leaderboard

Updated by hand. There is no hosted site, no automatic scoring, and no UI — see
`docs/V2_SCOPE.md`. Point estimates are reported with 95% Wilson intervals because at
these sample sizes adjacent rows are routinely indistinguishable.

### Arm 2 — compositional accuracy by nesting depth

| System | d2 | d3 | d4 | d5 | d6 | n/depth |
|---|---|---|---|---|---|---|
| gpt-4o-mini (prompt v2) | 0.800 [0.682, 0.882] | 0.683 [0.558, 0.787] | 0.517 [0.393, 0.638] | 0.650 [0.524, 0.758] | 0.367 [0.256, 0.493] | 60 |

Spearman rho = −0.9, exact one-sided permutation p = 0.0417, pooled 0.603 [0.547, 0.657]. Not monotonic. Full intervals, provenance and caveats: [`results/paper_data.md`](results/paper_data.md).

### Arm 1 — real criteria

| System | micro-F1 | macro-F1 | n |
|---|---|---|---|
| gpt-4o-mini (prompt v2) | 0.935 | 0.935 | 926 |

## Add your model

Implement one method:

```python
from criterialogic.models.base import Model
from criterialogic.tasks.base import Item, Prediction

class MyModel(Model):
    name = "my_model"

    def predict(self, item: Item) -> Prediction:
        # item.criterion is a LogicalForm; item.facts is a PatientFacts record.
        # Return a met/not-met label and a calibrated confidence in [0, 1].
        return Prediction(item_id=item.item_id, label=..., confidence=...)
```

Then produce and score a submission:

```bash
python scripts/make_submission.py --task compositional --model my_model --out sub.json
python scripts/make_submission.py --task compositional --score sub.json
```

Open a PR adding your result JSON under `results/leaderboard/` and your row to the table
above. Full details in [`CONTRIBUTING.md`](CONTRIBUTING.md).

**If that took you more than thirty minutes from a cold start, the instructions are at
fault and we want the issue.** The one-interface design is the only thing making outside
submission plausible for a project this size, so friction in it is a bug.

## From results to the paper

```bash
python scripts/collect_paper_data.py            # -> results/paper_data.md (paste-ready)
python scripts/collect_paper_data.py --verify   # diff the committed numbers extract against the artifacts
```

The collector recomputes every figure from the persisted per-item predictions, runs the
integrity gates (ceiling effects, degenerate confidence, rationale clustering, unanswerable
items, depth-trend significance and the n that would resolve each unresolved pair) as part
of collection, and prints a bracket with the command that fills it wherever an experiment
has not been run. `--verify` runs in CI and checks the five §7.1 depth rows plus Spearman
rho and the permutation p in `results/verify_extract.md`.

## Error taxonomy and annotation

Seven categories: negation/polarity, temporal, numeric threshold, logical composition,
entity conflation, implicit-knowledge gap, fabrication.

```bash
python scripts/annotation_export.py --results results/ \
    --depths 2,3,4,5,6 --n-per-depth 60 --n 200 --out annotation/
# both annotators fill category + clinical_judgement_required, blind to each other
python scripts/annotation_report.py --a annotation/errors_annotator1.csv \
                                    --b annotation/errors_annotator2.csv \
                                    --adjudication-out annotation/adjudication.csv
```

The codebook is [`docs/CODEBOOK.md`](docs/CODEBOOK.md) and is the instrument, not a
convenience. A heuristic labeller pre-sorts errors for triage; neither annotator sees its
output while labelling, and its agreement with the human consensus is reported separately.

## Reproducibility

Pinned dependencies, fixed seeds, and — recorded into every result file — the atom pool
digest, the snapshot id, the schema version, the prompt-renderer version, the
failure-labeller version, and the inference parameters the API *actually applied*
alongside the ones requested. Per-item predictions are persisted so any aggregate can be
recomputed without a rerun.

Both item sets are regenerable: same seed plus same depth list plus same atom pool gives a
byte-identical set, and the prompts are regenerable too.

**Model responses are not redistributed.** For the current `gpt-4o-mini` / prompt v2 run,
requested temperature 0.0 was applied (`effective_temperature` 0.0, `dropped_parameters`
empty). The response cache is not redistributed; the released per-item predictions are
the record of the run.

## Citation

See [`CITATION.cff`](CITATION.cff). License: MIT.
