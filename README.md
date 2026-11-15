# CriteriaLogic

**A controlled test of LLM reasoning over clinical-trial eligibility criteria, with item designs that vary nesting depth and expression size separately.**

Eligibility criteria nest AND/OR, negate, bound values, and scope things in time. A
screening system can score well on average and still fail on the constructions where a
wrong answer flips an eligibility decision. CriteriaLogic generates nested criteria whose
structure you set, with ground truth computed by a three-valued evaluator rather than
annotated. Depth and size have to be varied separately, because in a naturally built tree
they move together: in the original depth sweep the number of conditions grows about
2.3-fold per level, and depth tracks log₂ of it at r = 0.98. On `gpt-4o-mini`, accuracy
showed no detectable trend with depth at a fixed 14 conditions, and fell as the number of conditions doubled
at a fixed depth of 3 (leaderboard below).

Two arms, one snapshot, no gated data:

- **Arm 1 — real criteria.** Criteria segmented verbatim from a dated ClinicalTrials.gov
  API v2 snapshot, carrying real inclusion/exclusion polarity. Every mapped form has been
  checked against its source sentence (`annotation/arm1_verification.csv`, rule in
  `annotation/ARM1_VERIFICATION.md`); the headline uses verified forms only.
- **Arm 2 — compositional stress test.** Nested AND/OR/NOT expressions composed from atoms
  extracted from the same snapshot, in four item sets: the original depth sweep (depths 2–6)
  and mixed set (depths 1–4), in which size grows with depth; a size-matched set (depths
  2–6 at 14 conditions); and a fixed-depth size sweep (depth 3, 7 to 112 conditions).
- **Cross-cutting:** calibration and abstention (ECE, tie-aware selective accuracy).

Plus a seven-category reasoning-failure taxonomy and a published codebook. Two annotators
independently labelled all 179 errors from the evaluated runs; Cohen's κ = 0.337
[0.252, 0.420], and 0.165 [0.068, 0.266] without the Arm 1 errors outside the verified
subset. Both label sets are released. Codebook: `docs/CODEBOOK.md`.

> **Data policy:** public registry data and synthetic data only. Everything needed to reproduce both
> arms is committed. No data-use agreement, no credentials.

> **Reproducing the results?** `RUN.md` has the turnkey commands, and `make finish` runs
> the whole deterministic chain. Remaining work is tracked in `docs/TASKS.md`.

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

`scripts/preflight.py` checks the interpreter, the dependency, the resolved data directory, the
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

# the two designs that separate depth from size
python scripts/run_size_matched.py --model openai    # depths 2–6 at 14 conditions
python scripts/run_size_sweep.py --model openai      # depth 3, 7 to 112 conditions

# the original depth sweep, in which depth and size vary together
python scripts/run_eval.py --task compositional --depths 2,3,4,5,6 --n-per-depth 60 --model openai

# the real-criteria arm
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

The offline analyses that go with these runs (per-depth structure, the Arm 1 re-score) are
in `RUN.md` §8; `make revision` runs them.

## Leaderboard

Updated by hand. There is no hosted site, no automatic scoring, and no UI — see
`docs/V2_SCOPE.md`. Point estimates are reported with 95% Wilson intervals because at
these sample sizes adjacent rows are routinely indistinguishable.

### Arm 2 — depth at fixed size (size-matched set)

| System | d2 | d3 | d4 | d5 | d6 | n/depth |
|---|---|---|---|---|---|---|
| gpt-4o-mini (prompt v2) | 0.720 [0.625, 0.799] | 0.710 [0.615, 0.790] | 0.650 [0.552, 0.736] | 0.660 [0.563, 0.745] | 0.700 [0.604, 0.781] | 100 |

14 conditions, six groups and four NOT nodes at every depth; half the items met. Odds ratio
per depth level 0.959 [0.839, 1.096], likelihood-ratio p = 0.54: no detectable effect of
depth at fixed size. Details: [`results/size_matched/structure__openai.md`](results/size_matched/structure__openai.md).

### Arm 2 — size at fixed depth (size sweep)

| System | 7 | 14 | 28 | 56 | 112 | n/size |
|---|---|---|---|---|---|---|
| gpt-4o-mini (prompt v2) | 0.700 [0.604, 0.781] | 0.670 [0.573, 0.754] | 0.580 [0.482, 0.672] | 0.580 [0.482, 0.672] | 0.530 [0.433, 0.625] | 100 |

Depth 3 throughout; the columns are the number of conditions, with groups and NOT nodes in
the same ratio; half the items met at every size. Odds ratio per doubling 0.833
[0.732, 0.948], likelihood-ratio p = 0.0052; permutation p for a decline 0.0024. Details:
[`results/size_sweep/structure__openai.md`](results/size_sweep/structure__openai.md).

### Arm 2 — the original sets, in which depth and size vary together

| System | d2 | d3 | d4 | d5 | d6 | n/depth |
|---|---|---|---|---|---|---|
| gpt-4o-mini (prompt v2) | 0.800 [0.682, 0.882] | 0.683 [0.558, 0.787] | 0.517 [0.393, 0.638] | 0.650 [0.524, 0.758] | 0.367 [0.256, 0.493] | 60 |

Spearman rho = −0.9, exact one-sided permutation p = 0.0417, pooled 0.603 [0.547, 0.657]. Not monotonic. Full intervals, provenance and caveats: [`results/paper_data.md`](results/paper_data.md).

| System | d1 | d2 | d3 | d4 | n/depth |
|---|---|---|---|---|---|
| gpt-4o-mini (prompt v2) | 0.780 [0.689, 0.850] | 0.770 [0.678, 0.842] | 0.650 [0.552, 0.736] | 0.490 [0.394, 0.587] | 100 |

400 items generated separately from the sweep above. Spearman rho = −1.000, exact p = 0.0417
(the floor for four levels), monotonic, pooled 0.672 [0.625, 0.717]. The two sets agree within
0.033 at every overlapping depth. In both, the number of conditions grows about 2.3-fold per
depth level (5.2 at depth 2, 152.5 at depth 6), so neither can separate depth from size
([`results/depth_structure.md`](results/depth_structure.md)); the two designs above do.

### Arm 1 — real criteria

| System | Items | Accuracy | Macro-F1 | n |
|---|---|---|---|---|
| gpt-4o-mini (prompt v2) | verified forms, no rendering-convention items | 0.965 [0.942, 0.980] | 0.961 | 376 |
| gpt-4o-mini (prompt v2) | all items, as first released | 0.935 [0.917, 0.949] | 0.935 | 926 |

126 of the 463 mapped forms omit a required condition or change the meaning of their
sentence, so the all-items figure is not accuracy on real criteria
([`results/real_criteria_verified.md`](results/real_criteria_verified.md)). The verified items
are almost all single predicates: they measure predicate-level resolution, not full criteria.

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
has not been run. `--verify` runs in CI against `results/verify_extract.md` and
checks the five depth rows, Spearman rho, the permutation p, the Arm 1 composition
counts, the real-criteria micro-F1 and the accuracy range across depths — 36 figures in all. It does not
cover the agreement statistics; those live in `results/agreement.json`.

## Error taxonomy and annotation

Seven categories: negation/polarity, temporal, numeric threshold, logical composition,
entity conflation, implicit-knowledge gap, fabrication.

Two annotators labelled all 179 errors from the evaluated runs independently and blind to
each other. Cohen's κ = 0.337 [0.252, 0.420] over 179 items, 0.539 on real criteria and
0.088 on synthetic nested logic. Only `temporal` is applied reliably (κ = 0.821). Released:

| File | Contents |
|---|---|
| `annotation/annotator1_labels.csv` | annotator 1, all 179 rows |
| `annotation/annotator2_labels.csv` | annotator 2, all 179 rows |
| `annotation/report.json` | agreement statistics, also at `results/agreement.json` |
| `annotation/automatic_labels_HELD_BACK.csv` | heuristic labeller output, withheld during labelling |

Reproduce the reported figures from the released labels:

```bash
python scripts/annotation_report.py --a annotation/annotator1_labels.csv \
                                    --b annotation/annotator2_labels.csv \
                                    --automatic annotation/automatic_labels_HELD_BACK.csv \
                                    --out results/agreement.json
```

To annotate a new error set from scratch:

```bash
python scripts/annotation_export.py --results results/ --prompt-version 2 \
    --depths 2,3,4,5,6 --n-per-depth 60 --n 200 --out annotation/
# both annotators fill category + clinical_judgement_required, blind to each other
```

The codebook is [`docs/CODEBOOK.md`](docs/CODEBOOK.md) and is the instrument, not a
convenience. A heuristic labeller pre-sorts errors for triage and neither annotator saw its
output while labelling. **Adjudication was not run**, so no consensus label set exists and
no taxonomy distribution is reported; both annotators' raw labels are released instead.

## Reproducibility

Pinned dependencies, fixed seeds, and — recorded into every result file — the schema
version, the prompt-renderer version, the failure-labeller version, the item provenance
(the atom pool digest for compositional sets, the snapshot id for real criteria), and the
inference parameters the API *actually applied* alongside the ones requested. The snapshot
id `ctgov-2026-08-29` is stamped on the committed manifest. The real-criteria items were
built before that field existed, so `real_criteria` says `ctgov-unknown`; the compositional
generator does not record a snapshot id, and all four compositional result files carry the
same atom pool digest. Per-item predictions are persisted so any aggregate can be
recomputed without a rerun.

All four item sets are regenerable: the same seed, design parameters and atom pool give a
byte-identical set, and the prompts are regenerable too.

**Model responses are not redistributed.** For every `gpt-4o-mini` / prompt v2 run released
here, requested temperature 0.0 was applied (`effective_temperature` 0.0, `dropped_parameters`
empty). The response cache is not redistributed; the released per-item predictions are
the record of the run.

## Citation

See [`CITATION.cff`](CITATION.cff). Archived on Zenodo: all versions
[doi:10.5281/zenodo.24236661](https://doi.org/10.5281/zenodo.24236661); the
ClinicalTrials.gov snapshot on its own
[doi:10.5281/zenodo.24236790](https://doi.org/10.5281/zenodo.24236790).

License: MIT for the code. Registry text remains under the ClinicalTrials.gov terms and
conditions.
