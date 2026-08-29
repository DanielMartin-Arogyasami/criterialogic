# Datasheet for CriteriaLogic (Datasheet for Datasets, Gebru et al., 2021)
## Motivation
CriteriaLogic was created to measure whether NLP/LLM systems reason correctly over
the **logical structure** of clinical-trial eligibility criteria (nested AND/OR,
negation/polarity, temporal windows, numeric thresholds), which existing,
heterogeneous evaluations cannot compare across systems.
## Composition
- **Chia** (Kury et al., 2020): 1,000 Phase-IV trials; 12,409 annotated criteria,
  41,487 entities (15 types), 25,017 relations (12 types). CC-BY 4.0; releasable.
- **n2c2 2018 Track 1** (Stubbs et al., 2019): 288 longitudinal records, 13 criteria,
  binary met/not-met. **DUA-gated; not redistributed** — definitions are public and
  encoded in code; records require the Harvard DBMI DUA.
- **Compositional stress-test**: synthetic, generated deterministically from
  ClinicalTrials.gov criteria with a fixed seed; regenerable (`build_logic_set.py`).
## Collection
Chia and n2c2 are pre-existing, expert-annotated gold resources. The synthetic set
is machine-generated from public criteria; no human subjects are recruited and no
new patient data is collected.
## Preprocessing / harmonization
All sources map onto one logical-form schema (`schema/logical_form.py`). Mapping is
documented and validated (`schema/validators.py`). Numeric and temporal qualifiers
are captured as typed constraints.
## Uses
Research benchmark for eligibility-logic reasoning. **Not** a medical device; makes
no patient-care claims. Intended for offline model evaluation and error analysis.
## Distribution
Chia-derived artifacts + the toolkit are released under MIT/CC-BY on GitHub and
Hugging Face. n2c2 components are reproducible via the DUA pointer only.
## Maintenance
Versioned via `SCHEMA_VERSION` and package version; issues/PRs on GitHub.
