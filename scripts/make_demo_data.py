#!/usr/bin/env python3
"""Materialise the synthetic demo datasets to disk (matching + compositional)."""
from __future__ import annotations

import json
from pathlib import Path

from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import generate_matching_items
from criterialogic.tasks.compositional import generate_compositional_items


def main() -> None:
    out = Path("data/processed")
    out.mkdir(parents=True, exist_ok=True)
    match = generate_matching_items(harmonized_n2c2_criteria(), n_per_criterion=8, seed=13)
    comp = generate_compositional_items(n_per_depth=12, max_depth=3, seed=29)
    (out / "matching_demo.json").write_text(json.dumps([i.model_dump() for i in match], indent=2, default=str))
    (out / "compositional_demo.json").write_text(json.dumps([i.model_dump() for i in comp], indent=2, default=str))
    print(f"[wrote] {out}/matching_demo.json ({len(match)} items)")
    print(f"[wrote] {out}/compositional_demo.json ({len(comp)} items)")
if __name__ == "__main__":
    main()
