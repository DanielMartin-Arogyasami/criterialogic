# Remaining work

Superseded for v0.2. This file described the v0.1 work plan, including the Chia
structuring task, the n2c2 matching task, and the encoder baselines — all of which were
deliberately cut. See:

- **`docs/V2_SCOPE.md`** — what was cut, why, and the restoration path for each.
- **`results/paper_data.md` §6** — what is not yet measured and what each gap needs.
- **`results/DISCREPANCIES.md`** — open items where the code and the manuscript disagree.

## The short list, in order

1. **Re-run the depth sweep under prompt renderer v2.** The reported numbers were produced
   under v1, which has a disclosed rendering defect (paper_data.md §3). Needs an API key;
   costs roughly one sweep's worth of calls.
2. **Run the real-criteria arm.** Item construction is offline
   (`scripts/build_real_criteria.py`); the model rows need a key.
3. **The human annotation study.** Calibration session, then two annotators, >=150 items.
   The codebook is written and is on the critical path for nothing else.
4. **A second model.** The harness is not the obstacle; API access was.
5. **Log per-call cost.** Compute spend was reported in the author's earlier work and
   drew attention; the current adapter does not instrument it.
6. **Matching against real longitudinal records.** The single largest limitation of the
   release: patients are synthetic in both arms.

## Closed decisions

Recorded in `results/DISCREPANCIES.md` so they are not reopened:

- **Adjacent prior work by the same author** (entry 17) — omitted entirely from §2. Verified
  by a full-tree sweep: zero occurrences anywhere, and nothing inherited implicitly.
- **The committed snapshot's sampling frame** (entry 9) — kept as-is and described
  accurately; the recruiting filter is implemented but deliberately unapplied, because a
  rebuild invalidates every reported number.
- **Prompt renderer versioning** (entry 7) — v2 is the default; v1 retained so the exact
  prompts behind the reported numbers stay regenerable.

The v0.1 content of this file is in the git history.
