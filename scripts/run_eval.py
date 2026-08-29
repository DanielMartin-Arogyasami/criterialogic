#!/usr/bin/env python3
"""Thin wrapper so `python scripts/run_eval.py` works from a clone.
The implementation lives in `criterialogic.cli` (inside the installed package) so
that the `criterialogic-eval` console script also resolves after `pip install`.
"""
from criterialogic.cli import main

if __name__ == "__main__":
    main()
