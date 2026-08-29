# CriteriaLogic — collected data for the paper

Generated 2026-08-29T20:56:58+00:00 · package v0.1.0 · schema v0.1.0 · Python 3.12.10

> **INTEGRITY BANNER — read before using any number below.**
> Task C here uses the *real, public* n2c2 criterion definitions paired with **synthetic patients**, not the DUA-gated n2c2 records. Task D is **synthetic by construction**. The `rule_based` baseline evaluates an already-structured logical form and is therefore *the oracle itself*: its perfect scores are a software-validation artifact (paper §7.6), **not** an empirical finding. Only the `openai` rows are genuine model measurements, and even those are measured against synthetic patients.

## §3 Dataset composition (verified from code, not placeholders)

- n2c2 criteria encoded as LogicalForms: **13** (all 13 official tags)
- Task C items: **104** (13 criteria × 8 synthetic patients, seed 13); gold met-rate 0.6154
- Task D demo set: **36** items, depths {1: 12, 2: 12, 3: 12}, seed 29; gold met-rate 0.5833
- Task D large set: **400** items, depths {1: 100, 2: 100, 3: 100, 4: 100}; gold met-rate 0.4675
- Atom pool for Task D: **522** distinct atoms — atoms extracted from verbatim ClinicalTrials.gov eligibility text

### Per-criterion structural profile (feeds §3.2 and S2)

| Tag | Polarity | Nesting depth | Atoms | Temporal | Numeric |
|---|---|---|---|---|---|
| ABDOMINAL | inclusion | 1 | 3 | no | no |
| ADVANCED-CAD | inclusion | 2 | 12 | yes | yes |
| ALCOHOL-ABUSE | inclusion | 0 | 1 | yes | no |
| ASP-FOR-MI | inclusion | 0 | 1 | yes | no |
| CREATININE | inclusion | 0 | 1 | no | yes |
| DIETSUPP-2MOS | inclusion | 0 | 1 | yes | no |
| DRUG-ABUSE | inclusion | 0 | 1 | yes | no |
| ENGLISH | inclusion | 0 | 1 | no | no |
| HBA1C | inclusion | 0 | 1 | no | yes |
| KETO-1YR | inclusion | 0 | 1 | yes | no |
| MAJOR-DIABETES | inclusion | 1 | 4 | no | no |
| MAKES-DECISIONS | inclusion | 0 | 1 | no | no |
| MI-6MOS | inclusion | 0 | 1 | yes | no |

## §7.1 Main leaderboard (rows that can be filled today)

| Task | System | Headline metric | Value | ECE | n |
|---|---|---|---|---|---|
| C matching | rule_based (= oracle) | micro-F1 | **1.000** (macro 1.000) | 0.014 | 104 |
| C matching | negation_blind (illustrative) | micro-F1 | **0.923** (macro 0.921) | 0.223 | 104 |
| C matching | gpt-5-nano | micro-F1 | **0.952** (macro 0.948) | 0.165 | 104 |
| D compositional | rule_based (= oracle) | accuracy | **1.000** | 0.028 | 36 |
| D compositional | negation_blind (illustrative) | accuracy | **0.528** | 0.172 | 36 |
| D compositional | gpt-5-nano | accuracy | **1.000** | 0.199 | 36 |
| D compositional (400-item) | rule_based (= oracle) | accuracy | **1.000** | 0.020 | 400 |
| D compositional (400-item) | negation_blind (illustrative) | accuracy | **0.610** | 0.090 | 400 |

Tasks A and B have no rows: see *Cannot fill* below.

## §7.2 Accuracy versus logical nesting depth

| System | Set | d=1 | d=2 | d=3 | d=4 | Δ(shallowest→deepest) |
|---|---|---|---|---|---|---|
| rule_based | 36-item | 1.000 (n=12) | 1.000 (n=12) | 1.000 (n=12) | — | +0.000 |
| negation_blind | 36-item | 0.750 (n=12) | 0.583 (n=12) | 0.250 (n=12) | — | -0.500 |
| gpt-5-nano | 36-item | 1.000 (n=12) | 1.000 (n=12) | 1.000 (n=12) | — | +0.000 |
| rule_based | 400-item | 1.000 (n=100) | 1.000 (n=100) | 1.000 (n=100) | 1.000 (n=100) | +0.000 |
| negation_blind | 400-item | 0.680 (n=100) | 0.580 (n=100) | 0.600 (n=100) | 0.580 (n=100) | -0.100 |

The 400-item set is the one to cite for the depth claim; the 36-item set is too small (12 per depth) to resolve a monotonic trend.

## §7.3 Failure-taxonomy breakdown per system

| Task | System | Total errors | Category counts |
|---|---|---|---|
| matching | rule_based | 0 | none |
| matching | negation_blind | 8 | logical_composition=8 |
| matching | openai | 5 | temporal=5 |
| compositional | rule_based | 0 | none |
| compositional | negation_blind | 17 | logical_composition=7, negation_polarity=10 |
| compositional | openai | 0 | none |
| compositional_large | rule_based | 0 | none |
| compositional_large | negation_blind | 156 | logical_composition=80, negation_polarity=76 |

### Every gpt-5-nano error, itemized (feeds §7.3 and the S2 error appendix)

| Item | Task | Gold | Predicted | Conf. | Heuristic category |
|---|---|---|---|---|---|
| `match:ALCOHOL-ABUSE:000` | matching | not_met | met | 0.85 | temporal |
| `match:ASP-FOR-MI:000` | matching | not_met | met | 0.90 | temporal |
| `match:ASP-FOR-MI:001` | matching | not_met | met | 0.90 | temporal |
| `match:ASP-FOR-MI:003` | matching | not_met | met | 0.90 | temporal |
| `match:ASP-FOR-MI:006` | matching | not_met | met | 0.90 | temporal |

## §7.4 Calibration and abstention

| Task | System | ECE | Mean conf. | Abstentions | acc@10% | acc@20% | acc@30% | acc@40% | acc@50% | acc@60% | acc@70% | acc@80% | acc@90% | acc@100% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| matching | rule_based | 0.014 | 0.9856 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| matching | negation_blind | 0.223 | 0.7 | 0 | 0.727 | 0.714 | 0.812 | 0.857 | 0.885 | 0.905 | 0.918 | 0.929 | 0.915 | 0.923 |
| matching | openai | 0.165 | 0.8272 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.984 | 0.945 | 0.941 | 0.947 | 0.952 |
| compositional | rule_based | 0.028 | 0.9722 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| compositional | negation_blind | 0.172 | 0.7 | 0 | 1.000 | 0.750 | 0.818 | 0.733 | 0.722 | 0.682 | 0.654 | 0.586 | 0.545 | 0.528 |
| compositional | openai | 0.199 | 0.8011 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## §7.6 Reference-implementation validation (software, not findings)

- rule_based Task C micro-F1 = **1.000**, Task D accuracy = **1.000**, total errors = 0 — perfect by construction.
- negation_blind error signature, Task C: {'logical_composition': 8}
- negation_blind error signature, Task D: {'negation_polarity': 10, 'logical_composition': 7}
- negation_blind depth curve (400-item): {'1': 0.68, '2': 0.58, '3': 0.6, '4': 0.58}
- Rule-based == oracle on already-structured forms, so its perfect scores are a software-validation artifact, NOT an empirical finding.

## §5 Taxonomy codebook (as implemented)

| Category | Definition |
|---|---|
| negation_polarity | Inclusion/exclusion or NOT-scope flipped. |
| temporal | Temporal window or tense reasoning error. |
| numeric_threshold | Comparator or boundary value error. |
| logical_composition | AND/OR/NOT composition resolved incorrectly. |
| entity_conflation | Distinct clinical entities conflated. |
| implicit_knowledge | Failed required unstated inference. |
| fabrication | Asserted a constraint absent from the criterion. |
| none | No attributable failure. |

Annotation inputs are staged at `results/errors_openai_matching.csv` and `results/errors_openai_compositional.csv`, each with a blank `human_category` column. Cohen's κ and test–retest agreement remain uncomputed pending the human pass.

## §9 Reproducibility metadata

- Python 3.12.10 on Windows-11-10.0.26200-SP0
- LLM: `gpt-5-nano`, temperature requested 0.0, effective **none (API default)** — gpt-5-nano rejects a custom temperature; the adapter drops it and retries, so every completion used the API default. The dropped parameter is not recorded per call — see results/DISCREPANCIES.md entry 3.
- Cached LLM responses: 143
- Packages: openai==3.6.0, pydantic==2.13.5, pytest==9.1.1, ruff==0.16.5
- Tests: 55 passed in 0.54s · Lint: All checks passed!
- Seeds: {'matching': 13, 'compositional': 29, 'large_compositional': 29}

## Cannot fill — what the paper still needs

- **7.1 Task A (structuring)** — Chia corpus not downloaded and no structuring model implemented (entity F1 / relation F1 / exact match unavailable).
- **7.1 Task B (typing & polarity)** — Requires Chia-derived labels and a classification model; tasks/typing_polarity.py is a task-name contract only.
- **7.1 Task C on REAL patients** — n2c2 2018 records are DUA-gated and absent; all Task C numbers here use synthetic patients over the real public criterion definitions.
- **6. Encoder baselines** — models/encoder.py raises NotImplementedError; needs transformers/torch plus a fine-tuned checkpoint (BioClinicalBERT / PubMedBERT / BioBERT).
- **6. Open-weight LLMs** — models/llm_local.py is a stub; needs an HF/vLLM runtime.
- **6. Additional API LLMs** — The available API project grants access to gpt-5-nano only; GPT-4-class and Claude-class models returned 403 model_not_found.
- **7.5 Ablations** — No prompt-design, few-shot-count, or retrieval ablation has been run; the toolkit ships a single fixed zero-shot prompt.
- **5. Human-vs-automatic kappa** — Requires the domain expert to fill human_category in results/errors_openai_*.csv, then run taxonomy.reliability.
- **5. Test-retest kappa** — Requires a second annotation pass after a washout interval.

## Discrepancies between the paper draft and the implementation

1. **Paper Sec. 3.4 vs criterialogic/tasks/compositional.py::_atom_pool**
   - Paper: Task D atoms are 'extracted from real ClinicalTrials.gov criteria'.
   - Reality: Atoms are now extracted from verbatim ClinicalTrials.gov v2 eligibility text into data/ctgov_atom_pool.json, each carrying its source NCT ID, source sentence, and the trial's first-posted date. The generator raises if the pool is absent instead of falling back to the n2c2 leaves.
   - Action: See results/DISCREPANCIES.md entry 1 for the four qualifications the Sec. 3.4 wording must respect (synthetic nesting, conservative extraction yield, polarity-free predicates, dated contamination claim).
2. **Paper Sec. 7.2 hypothesis**
   - Paper: Accuracy declines monotonically with nesting depth.
   - Reality: See 7.2 table: not monotonic for every system at these sample sizes.
   - Action: State the observed pattern; do not assert monotonicity without wider n.
