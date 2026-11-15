"""Assemble manuscript supplements S1, S3, S4, S5 from files already in the repo.

Writes ``supplement/``. Does not invent figures: tables are copied from
``results/paper_data.md`` and from the results tables added in revision, prompts
and the v1/v2 rendering difference are taken from ``criterialogic.models.llm_api``,
and S5 is ``DATASHEET.md`` verbatim. S7 is two repository files and is not copied.
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
    "results/size_matched/compositional__openai.json",
    "results/size_sweep/compositional__openai.json",
    "results/compositional__rule_based.json",
    "results/compositional__negation_blind.json",
    "results/real_criteria__rule_based.json",
    "results/real_criteria__negation_blind.json",
    "results/size_matched/compositional__rule_based.json",
    "results/size_matched/compositional__negation_blind.json",
    "results/size_sweep/compositional__rule_based.json",
    "results/size_sweep/compositional__negation_blind.json",
]

ITEM_SET_FILES = [
    "data/processed/logic_set_depth_sweep.json",
    "data/processed/logic_set_mixed.json",
    "data/processed/logic_set_size_matched.json",
    "data/processed/logic_set_size_sweep.json",
]

LABEL_FILES = [
    "annotation/annotator1_labels.csv",
    "annotation/annotator2_labels.csv",
]

#: Results tables added in revision, embedded in S3 under these headings.
REVISION_TABLES = [
    ("Per-depth structure of the original depth sweep and mixed set",
     "results/depth_structure.md"),
    ("Size-matched set: depth varies at 14 leaves",
     "results/size_matched/structure__openai.md"),
    ("Fixed-depth size sweep: size varies at depth 3",
     "results/size_sweep/structure__openai.md"),
    ("Real-criteria arm on the verified subsets",
     "results/real_criteria_verified.md"),
    ("Power of the size-matched design, and a size-only model",
     "results/size_checks.md"),
]

#: Edits to the copied paper_data.md text. Its headings carry the submitted manuscript's
#: section numbers, and S3 goes with the revision, where the mixed set moved into §7.1 and
#: the renderer check to §7.8. Its pointers to "the end of this file" mean the integrity
#: gates, which S3 places directly after the tables. Text that is not found fails loudly
#: rather than leaving a stale number or a dangling pointer.
PAPER_DATA_EDITS = [
    ("## Section 7.2 — the mixed-depth set", "## Section 7.1 — the mixed-depth set"),
    ("## Section 7.3 — exposure to the renderer defect",
     "## Section 7.8 — exposure to the renderer defect"),
    ("Read the integrity gates at the end before quoting",
     "Read the integrity gates below before quoting"),
    ("See the end of this file.", "See the integrity gates below."),
]

GATES_NOTE = (
    "The collector's reporting rules for the original runs. A [BLOCK] names a way a "
    "figure must not be reported, not a failed computation."
)


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


def _paper_data_gates(text: str) -> str:
    """The integrity gates, which the summary line at the top of paper_data.md points to."""
    start, stop = text.find("## Integrity gates\n"), text.find("## Provenance")
    if start < 0 or stop < start:
        raise ValueError("results/paper_data.md has no Integrity gates section before Provenance")
    heading = "## Integrity gates\n"
    return heading + "\n" + GATES_NOTE + "\n" + text[start + len(heading):stop].rstrip() + "\n"


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


def _edit_paper_data(text: str) -> str:
    for old, new in PAPER_DATA_EDITS:
        if old not in text:
            raise ValueError(f"results/paper_data.md no longer contains {old!r}")
        text = text.replace(old, new)
    return text


def _demote(text: str) -> str:
    """Push every Markdown heading down one level, so a copied file nests under S3."""
    return "\n".join("#" + ln if ln.startswith("#") else ln for ln in text.splitlines()) + "\n"


def _embed(title: str, rel: str) -> str:
    """A results table file under its own S3 heading, with the file's title dropped."""
    body = _read(rel).splitlines()
    if body and body[0].startswith("# "):
        body = body[1:]
    return f"## {title}\n\nSource: `{rel}`.\n" + _demote("\n".join(body))


def _listed(rels: list[str]) -> list[str]:
    for rel in rels:
        if not (ROOT / rel).is_file():
            raise FileNotFoundError(ROOT / rel)
    return [f"- `{rel}`" for rel in rels]


def assemble_s3() -> str:
    paper_data = _read("results/paper_data.md")
    tables = _demote(_edit_paper_data(
        _cut_paper_data_tables(paper_data) + "\n" + _paper_data_gates(paper_data)
    ))
    lines = [
        "# S3. Per-level and per-item result tables\n",
        "The per-depth and calibration tables of the original runs, with the collector's "
        "integrity gates, are copied from `results/paper_data.md`, which "
        "`scripts/collect_paper_data.py` recomputes from persisted per-item predictions; "
        "their section numbers follow the revised manuscript. The tables added in "
        "revision follow them: for each of the four "
        "compositional item sets, the structure of every level (leaves, AND/OR/NOT counts, "
        "undocumented leaves, prompt length, gold and model met rates) with its accuracy "
        "and the item-level trend; and the real-criteria arm on the verified subsets. "
        "Per-item predictions themselves are the JSON run files listed at the end; they "
        "are not inlined. Human labels cover the 179 `gpt-4o-mini` errors only "
        "(`annotation/annotator1_labels.csv`, `annotation/annotator2_labels.csv`). "
        "Diagnostic and legacy runs have no human labels. The full agreement record is "
        "`results/agreement.json`.\n",
        tables,
    ]
    lines += [_embed(title, rel) for title, rel in REVISION_TABLES]
    lines.append("## Item sets\n")
    lines += _listed(ITEM_SET_FILES)
    lines.append("")
    lines.append("## Per-item prediction files\n")
    lines += _listed(RUN_FILES)
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
        "copied here. S6 is the AI-assistance paragraph in the manuscript. S7 is "
        "`annotation/ARM1_VERIFICATION.md` with `annotation/arm1_verification.csv` "
        "and is not copied here.\n\n"
        "| File | Source |\n|---|---|\n"
        "| `S1_schema.md` | `criterialogic/schema/logical_form.py`, "
        "`criterialogic/schema/validators.py` |\n"
        "| `S3_results.md` | `results/paper_data.md` tables and integrity gates; "
        "`results/depth_structure.md`, `results/size_matched/structure__openai.md`, "
        "`results/size_sweep/structure__openai.md`, `results/real_criteria_verified.md`, `results/size_checks.md`; "
        "item-set and run JSON paths; label-file row counts |\n"
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
