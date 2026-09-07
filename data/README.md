# Data

`data/raw/` and `data/processed/` are **gitignored**. The ClinicalTrials.gov snapshot
below *is* committed: it is small, US Government public domain, and checking it in is
what makes both benchmark arms reproducible with no network access and no credentials.

There is no licence-restricted component in v0.2. Nothing here needs a data-use
agreement.

## ClinicalTrials.gov snapshot (public domain, US Government)

- `ctgov_cache/` — raw API v2 records, one JSON per NCT ID, plus `MANIFEST.json`
  recording the exact query, the sampling frame field by field, the fetch timestamp, and
  a snapshot id. A cached study is never re-fetched.
- `ctgov_atom_pool.json` — the atom pool the compositional stress test composes over.
  Each atom carries its source NCT ID, the verbatim sentence it was extracted from, that
  trial's first-posted date, and the extraction rule that fired, so every generated item
  traces back to real trial text.

### The frame that produced the committed snapshot

Read it from `ctgov_cache/MANIFEST.json` rather than from any prose, here or in the
paper. As shipped it is Phase-4 interventional studies first posted on or after
2026-01-01, sorted by first-posted date descending, 300 studies, fetched 2026-08-29.
There is **no** recruitment-status filter on the committed snapshot.

`StudyQuery` supports `overall_status` (and `scripts/fetch_ctgov_snapshot.py
--recruiting`) for a status-restricted rebuild, which is the better frame for a paper
about screening systems: recruiting trials are the ones such a system is pointed at.
It is not applied to the committed snapshot for one reason only — see below.

### Rebuilding invalidates published numbers

The pool's SHA-256 is stamped on every generated item. A new pool means new items, which
means every reported result has to be regenerated, which for the LLM rows means new API
calls. Before rebuilding, read `results/paper_data.md` and decide whether you are
replacing the reported results or forking a new version of them.

```bash
# rebuild in place (invalidates results)
python scripts/fetch_ctgov_snapshot.py --limit 300 --first-posted-from 2026-01-01
# recruiting-restricted rebuild, e.g. for v0.3
python scripts/fetch_ctgov_snapshot.py --recruiting --limit 300 --first-posted-from 2026-06-01
# rebuild the pool from the existing cache, no requests
python scripts/fetch_ctgov_snapshot.py --offline
```

### Why the date filter matters

`--first-posted-from` is the contamination control. Restricting to trials first posted
after an evaluated model's training cutoff is what makes "these criteria were not in
training" evidence rather than an assumption. It is a property of the pool file, not of
the method: the committed pool's atoms come from trials first posted between 2026-06-30
and 2026-08-28, and a rebuild with a different date changes that range.

## Extraction is deliberately conservative

The extractor is a rule-based pass, not a parser. A sentence either matches one of its
patterns or is skipped and counted as unmapped; nothing is coerced into an atom to raise
the yield. Coordinated phrases, comma enumerations, and bounds stated relative to a
reference range ("<= 3x ULN") are skipped rather than approximated, so the pool
under-represents complex criteria by design. The yield ratio is recorded in the pool
file under `extraction` and reported in the manuscript.
