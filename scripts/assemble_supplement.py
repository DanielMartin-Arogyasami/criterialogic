"""Assemble manuscript supplements S1, S3, S4, S5 from files already in the repo.

Writes ``supplement/``. Does not invent figures: tables are copied from
``results/paper_data.md``, prompts and the v1/v2 rendering difference are taken
from ``criterialogic.models.llm_api``, and S5 is ``DATASHEET.md`` verbatim.
"""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "supplement"

RUN_FILES = [
    "results/compositional__openai.json",
    "results/real_criteria__openai.json",
    "results/mixed_v2/compositional__openai.json",
    "results/compositional__rule_based.json",
    "results/compositional__negation_blind.json",
    "results/real_criteria__rule_based.json",
    "results/real_criteria__negation_blind.json",
]

LABEL_FILES = [
    "annotation/annotator1_labels.csv",
    "annotation/annotator2_labels.csv",
]


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def _cut_paper_data_tables(text: str) -> str:
    """Per-depth and calibration tables only. The human-annotation JSON dump in
    paper_data.md is truncated by the collector; the full record is agreement.json."""
    stop = text.find("## Section 7.5")
    if stop < 0:
        raise ValueError("results/paper_data.md has no Section 7.5 heading")
    return text[:stop].rstrip() + "\n"


def assemble_s1() -> str:
    schema = _read("criterialogic/schema/logical_form.py")
    validators = _read("criterialogic/schema/validators.py")
    return (
        "# S1. Full schema specification\n\n"
        "Reproduced from the released repository. Node types, constraints, "
        "validators and canonicalisation are the contents of these two files. "
        "Do not treat this copy as independent of the package: "
        "`SCHEMA_VERSION` in `logical_form.py` is the version stamp on every record.\n\n"
        "Source: `criterialogic/schema/logical_form.py`\n\n"
        "```python\n"
        f"{schema.rstrip()}\n"
        "```\n\n"
        "Source: `criterialogic/schema/validators.py`\n\n"
        "```python\n"
        f"{validators.rstrip()}\n"
        "```\n"
    )


def assemble_s3() -> str:
    tables = _cut_paper_data_tables(_read("results/paper_data.md"))
    lines = [
        "# S3. Per-depth and per-item result tables\n",
        "Per-depth tables below are copied from `results/paper_data.md`, which "
        "`scripts/collect_paper_data.py` recomputes from persisted per-item "
        "predictions. Per-item predictions themselves are the JSON run files "
        "listed at the end; they are not inlined. Human labels cover the 179 "
        "`gpt-4o-mini` errors only (`annotation/annotator1_labels.csv`, "
        "`annotation/annotator2_labels.csv`). Diagnostic and legacy runs have "
        "no human labels. The full agreement record is `results/agreement.json`.\n",
        tables,
        "## Per-item prediction files\n",
    ]
    for rel in RUN_FILES:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        lines.append(f"- `{rel}`")
    lines.append("")
    lines.append("## Human labels (`gpt-4o-mini` errors only)\n")
    for rel in LABEL_FILES:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open(encoding="utf-8", newline="") as fh:
            n = sum(1 for _ in csv.DictReader(fh))
        lines.append(f"- `{rel}` ({n} rows)")
    lines.append("")
    lines.append("- `results/agreement.json` (Cohen's κ and the rest of §7.5)")
    lines.append("")
    return "\n".join(lines)


def assemble_s4() -> str:
    from criterialogic.models.llm_api import (
        _SYSTEM_V1,
        _SYSTEM_V2,
        render_patient,
    )
    from criterialogic.oracle import Fact, PatientFacts

    facts = PatientFacts(
        record_id="s4-currency",
        facts={"aspirin": Fact(present=True, current=False)},
    )
    v1_patient = render_patient(facts, prompt_version="1")
    v2_patient = render_patient(facts, prompt_version="2")
    return (
        "# S4. Prompts\n\n"
        "The zero-shot prompt, both renderer versions, taken from "
        "`criterialogic/models/llm_api.py`. The reported runs used version 2. "
        "Version 1 is retained so the previously released prompts can be "
        "regenerated. The user message is the same frame in both versions; "
        "only the question sentence, the criterion wrapper, and the patient "
        "currency line differ.\n\n"
        "## System prompt, version 1\n\n"
        f"```\n{_SYSTEM_V1}\n```\n\n"
        "## System prompt, version 2\n\n"
        f"```\n{_SYSTEM_V2}\n```\n\n"
        "## User message\n\n"
        "Version 1 asks `Does the patient satisfy the criterion?`\n\n"
        "Version 2 asks `Does the criterion's condition hold for this patient?`\n\n"
        "```\n"
        "CRITERION:\n"
        "{render_criterion(item.criterion, prompt_version)}\n\n"
        "PATIENT FACTS (entities not listed are undocumented):\n"
        "{render_patient(item.facts, prompt_version)}\n\n"
        "{question}\n"
        "```\n\n"
        "## Rendering difference\n\n"
        "v1 emits `currently active` only when `Fact.current` is true and emits "
        "nothing when it is false, so a present-but-not-current finding is "
        "indistinguishable from a finding whose currency was never recorded. "
        "v2 states the currency of every present finding. The pair below is "
        "produced by `render_patient` on `Fact(present=True, current=False)` "
        "(the fixture in `tests/test_llm_api.py`).\n\n"
        "Version 1:\n\n"
        f"```\n{v1_patient}\n```\n\n"
        "Version 2:\n\n"
        f"```\n{v2_patient}\n```\n\n"
        "v2 also wraps verbatim registry text in `<criterion_text>` markers "
        "named as data in the system prompt. Version 1 interpolates that text "
        "unmarked.\n"
    )


def assemble_s5() -> str:
    body = _read("DATASHEET.md")
    return (
        "# S5. Datasheet for datasets\n\n"
        "Verbatim copy of `DATASHEET.md` in the released repository, following "
        "Gebru et al. (2021).\n\n"
        f"{body}"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "S1_schema.md": assemble_s1(),
        "S3_results.md": assemble_s3(),
        "S4_prompts.md": assemble_s4(),
        "S5_datasheet.md": assemble_s5(),
    }
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8", newline="\n")
    for rel in LABEL_FILES:
        shutil.copy2(ROOT / rel, OUT / Path(rel).name)
    index = (
        "# Supplementary files (S1, S3–S5)\n\n"
        "Assembled by `python scripts/assemble_supplement.py` from files "
        "already in the repository. S2 is `docs/CODEBOOK.md` and is not "
        "copied here. S6 is the AI-assistance paragraph in the manuscript.\n\n"
        "| File | Source |\n|---|---|\n"
        "| `S1_schema.md` | `criterialogic/schema/logical_form.py`, "
        "`criterialogic/schema/validators.py` |\n"
        "| `S3_results.md` | `results/paper_data.md` tables; run JSON paths; "
        "label-file row counts |\n"
        "| `annotator1_labels.csv` | `annotation/annotator1_labels.csv` |\n"
        "| `annotator2_labels.csv` | `annotation/annotator2_labels.csv` |\n"
        "| `S4_prompts.md` | `criterialogic/models/llm_api.py` "
        "(`_SYSTEM_V1`, `_SYSTEM_V2`, `render_patient`) |\n"
        "| `S5_datasheet.md` | `DATASHEET.md` |\n"
    )
    (OUT / "README.md").write_text(index, encoding="utf-8", newline="\n")
    written = ", ".join(sorted(p.name for p in OUT.iterdir()))
    print(f"[wrote] {OUT} ({written})")


if __name__ == "__main__":
    main()
