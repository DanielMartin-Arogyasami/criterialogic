# Legacy scripts — provenance for the v0.1/v0.2 results

**These scripts do not run against the current package.** They import
`criterialogic.data.harmonize.harmonized_n2c2_criteria` and
`criterialogic.data.synthetic.generate_matching_items`, which were removed in v0.2
(see `../docs/V2_SCOPE.md`). They are kept because they produced the reported results and
the audit that shaped them, and deleting them would remove the provenance for numbers the
manuscript cites.

| Script | What it produced |
|---|---|
| `run_missing.py` | The depth sweep in `results/missing/missing_runs.json` — the paper's headline result. Depth-*d* sets were built with `generate_compositional_items(n_per_depth=60, max_depth=d, seed=101+d)` and filtered to the depth-*d* slice. Also produced the 400-item mixed-depth set (seed 29) and the suspect-item dump. |
| `collect_paper_data.py` | `results/paper_data.json` / `.md` — the v0.1 collection pass, including the n2c2-criteria matching task that v0.2 removed. |
| `audit_paper_data.py` | `results/AUDIT.md` and `results/missing/AUDIT_missing.md` — the integrity audit that found the degenerate selective-accuracy curves, the rationale clustering, the unanswerable items, and the inference-parameter contradiction. Most of the v0.2 changes trace to a finding in here. |

## Reproducing the reported item sets from the current package

The depth sets remain regenerable without these scripts:

```python
from criterialogic.tasks.compositional import regenerate_reported_depth_set
items = regenerate_reported_depth_set(depth=5)     # seed defaults to 101 + depth
```

That function preserves the original generation path deliberately. New work should use
`generate_compositional_items(depths=[d])`, which varies only depth rather than depending
on how many random draws the shallower depths consumed first.

## Do not cite v0.1 numbers

`results/paper_data.md` reports a matching task built on the n2c2 criterion definitions
paired with synthetic patients. The audit found that four of its five reported model errors
were on items whose gold label rested on a fact the prompt never stated, so they were
unanswerable rather than temporal-reasoning failures. It also reports a failure-taxonomy
distribution produced by labeller v1, whose decision order made only two of seven
categories reachable. Both are superseded by `results/SECTION7.md`.
