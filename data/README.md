# Data
`data/raw/` and `data/processed/` are **gitignored**. Nothing here is committed.
## Chia (releasable, CC-BY)
- figshare: https://doi.org/10.6084/m9.figshare.11855817
- Hugging Face: https://huggingface.co/datasets/bigbio/chia
- Place `.txt`/`.ann` under `data/raw/chia/`; load via `criterialogic.data.loaders.chia`.
## ClinicalTrials.gov (public)
- Fetched at runtime by `criterialogic.data.loaders.ctgov` (API v2). No download needed.
## n2c2 2018 Track 1 — Cohort Selection (DUA-GATED, NOT redistributable)
- Request access: https://n2c2.dbmi.hms.harvard.edu/
- After approval, place patient XML under `data/raw/n2c2_2018/`.
- The 13 criterion **definitions** are public and live in code
  (`criterialogic.data.n2c2_criteria`); only the patient records are restricted.
- We **never** commit or redistribute n2c2 records — only this pointer + the harness.
