# CriteriaLogic — docs

## Repository layout

```
criterialogic/
  schema/logical_form.py     # the canonical logical form (pydantic v2)
  schema/validators.py       # corpus-level checks (ids, versions, split leakage)
  oracle.py                  # three-valued Kleene evaluator (ground truth + rule-based engine)
  data/
    loaders/ctgov.py         # ClinicalTrials.gov API v2: snapshot + atom extraction
    real_criteria.py         # Arm 1: segment snapshot criteria into LogicalForms
    atom_pool.py             # the atom pool and its provenance
    synthetic.py             # seeded synthetic patient-fact generator
    harmonize.py             # source -> schema seam
    splits.py                # trial-keyed splits with a leakage check
  tasks/
    real_criteria.py         # Arm 1 items
    compositional.py         # Arm 2: depth-parameterised generator
    calibration.py           # cross-cutting layer (no separate item set)
  models/                    # Model interface + rule_based, negation_blind, openai
  metrics/
    stats.py                 # Wilson, Spearman + permutation p, kappa CI (stdlib only)
    calibration.py           # ECE, tie-aware selective accuracy
    logic.py                 # accuracy by depth + trend statistics
    decision.py              # met/not-met scoring
    classification.py        # P/R/F1 primitives
  taxonomy/
    categories.py            # the seven categories
    annotate.py              # heuristic labeller (triage aid, versioned)
    reliability.py           # two-annotator workflow, kappa, adjudication
  eval/                      # runner + markdown report
  leaderboard/               # submission validation + scoring

scripts/
  fetch_ctgov_snapshot.py    # freeze the snapshot, build the atom pool
  build_real_criteria.py     # Arm 1 forms + yield statistics
  build_logic_set.py         # Arm 2 item sets
  run_eval.py                # thin wrapper over criterialogic.cli
  make_submission.py         # produce and score a leaderboard submission
  annotation_export.py       # draw the sample, write blind annotator files
  annotation_report.py       # kappa, disagreements, consensus, third signal
  collect_paper_data.py      # every paper number + integrity gates; --verify diffs the paper
  preflight.py               # can this installation run? environment + data + both arms

docs/
  CODEBOOK.md                # the annotation instrument
  V2_SCOPE.md                # what was deferred and why
```

## Key documents

- **`docs/CODEBOOK.md`** — the annotation codebook. Read this before labelling anything.
- **`docs/V2_SCOPE.md`** — what v0.2 cut, why, and how to restore it.
- **`results/paper_data.md`** — the reported results, with the provenance and caveats each
  number carries.
- **`results/DISCREPANCIES.md`** — the register of places where the manuscript and the
  code disagree, or where the code cannot support a claim the manuscript wants to make.
- **`DATASHEET.md`** — datasheet for the released data.

## Statistics without a scientific stack

`criterialogic/metrics/stats.py` is standard-library only and imports nothing from the
rest of the package, so the arithmetic behind every reported interval can be read and
executed without installing pydantic:

```bash
python -c "
import importlib.util as u
s = u.spec_from_file_location('s', 'criterialogic/metrics/stats.py')
m = u.module_from_spec(s); s.loader.exec_module(m)
print(m.wilson_interval(36, 60))
"
```
