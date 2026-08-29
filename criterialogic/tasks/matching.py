"""Task C — patient–criterion matching (met / not-met). Gold: n2c2 2018.
In the runnable demo the items are built by `data.synthetic.generate_matching_items`
over the public n2c2 criterion definitions with synthetic patients. With real
DUA-obtained n2c2 records, swap in `data.loaders.n2c2` as the item source; the
task contract (an `Item` with a `criterion`, `facts`, and gold `met`) is identical.
"""
from criterialogic.data.synthetic import generate_matching_items  # noqa: F401

TASK_NAME = "matching"
