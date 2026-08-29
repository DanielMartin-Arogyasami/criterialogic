# Data
`data/raw/` and `data/processed/` are **gitignored**; no corpus is committed there.
The ClinicalTrials.gov cache and atom pool below *are* committed: they are small, public
domain, and checking them in is what makes Task D reproducible without network access.
## Chia (releasable, CC-BY)
- figshare: https://doi.org/10.6084/m9.figshare.11855817
- Hugging Face: https://huggingface.co/datasets/bigbio/chia
- Place `.txt`/`.ann` under `data/raw/chia/`; load via `criterialogic.data.loaders.chia`.
## ClinicalTrials.gov (public domain, US Government)
- `ctgov_cache/` — raw API v2 records, one JSON per NCT ID, plus `MANIFEST.json` recording
  the exact query that produced them. Never re-fetched on a cache hit.
- `ctgov_atom_pool.json` — the Task D atom pool. Each atom carries its source NCT ID, the
  verbatim sentence it was extracted from, that trial's first-posted date, and the
  extraction rule that fired, so every generated item traces back to real trial text.
- Rebuild: `python scripts/fetch_ctgov_atoms.py --limit 300 --first-posted-from YYYY-MM-DD`
  (add `--offline` to rebuild the pool from the existing cache without any request).
- The date filter is the contamination control: restricting to trials first posted after a
  model's training cutoff is what gives §3.5 evidence rather than an assumption.
## n2c2 2018 Track 1 — Cohort Selection (DUA-GATED, NOT redistributable)
- Request access: https://n2c2.dbmi.hms.harvard.edu/
- After approval, place patient XML under `data/raw/n2c2_2018/`.
- The 13 criterion **definitions** are public and live in code
  (`criterialogic.data.n2c2_criteria`); only the patient records are restricted.
- We **never** commit or redistribute n2c2 records — only this pointer + the harness.
