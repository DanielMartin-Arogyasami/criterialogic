"""Load + parse the Chia corpus (brat standoff) into LogicalForm records.
Chia ships as brat .txt/.ann pairs: T-lines are entities (type + span + text),
R-lines are typed relations including the AND/OR connectors and Has_negation /
Has_value / Has_temporal. Chia is CC-BY and fully releasable.
This is a first-pass mapper for the common patterns; the DAG->tree assembly for
deeply nested criteria and a few rarer relation types are marked TODO. Download
Chia via `scripts/download_data.py` (figshare / Hugging Face `bigbio/chia`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from criterialogic.schema.logical_form import (
    Atom,
    Entity,
    EntityType,
    Expression,
    LogicalForm,
    Not,
    Polarity,
    Source,
)

# Chia entity type -> our coarse EntityType
_TYPE_MAP = {
    "Condition": EntityType.CONDITION,
    "Drug": EntityType.DRUG,
    "Procedure": EntityType.PROCEDURE,
    "Measurement": EntityType.MEASUREMENT,
    "Observation": EntityType.OBSERVATION,
    "Person": EntityType.PERSON,
    "Device": EntityType.DEVICE,
    "Visit": EntityType.VISIT,
    "Mood": EntityType.OTHER,
    "Value": EntityType.OTHER,
    "Temporal": EntityType.OTHER,
    "Negation": EntityType.OTHER,
    "Qualifier": EntityType.OTHER,
}
@dataclass
class _BratEntity:
    tid: str
    etype: str
    text: str
@dataclass
class _BratDoc:
    entities: dict[str, _BratEntity] = field(default_factory=dict)
    relations: list[tuple[str, str, str]] = field(default_factory=list)  # (type, argA, argB)
def parse_ann(ann_text: str) -> _BratDoc:
    doc = _BratDoc()
    for line in ann_text.splitlines():
        if line.startswith("T"):
            m = re.match(r"(T\d+)\t(\S+)[^\t]*\t(.*)", line)
            if m:
                tid, etype = m.group(1), m.group(2)
                doc.entities[tid] = _BratEntity(tid, etype, m.group(3))
        elif line.startswith("R"):
            m = re.match(r"R\d+\t(\S+) Arg1:(\S+) Arg2:(\S+)", line)
            if m:
                doc.relations.append((m.group(1), m.group(2), m.group(3)))
    return doc
def _to_atom(ent: _BratEntity) -> Atom:
    return Atom(entity=Entity(text=ent.text, type=_TYPE_MAP.get(ent.etype, EntityType.OTHER)))
def doc_to_logical_forms(doc: _BratDoc, trial_id: str) -> list[LogicalForm]:
    """First-pass assembly: negation wraps its target; AND/OR connectors group entities.
    TODO: full DAG->tree reduction for multi-level nesting; Has_value/Has_temporal
    attachment onto Atom constraints (requires parsing Value/Temporal entity text).
    """
    negated = {b for (t, a, b) in doc.relations if t.lower().startswith("has_neg")}
    forms: list[LogicalForm] = []
    idx = 0
    for tid, ent in doc.entities.items():
        if ent.etype in {"Value", "Temporal", "Negation", "Qualifier", "Mood"}:
            continue
        expr: Expression = _to_atom(ent)
        if tid in negated:
            expr = Not(operand=expr)
        forms.append(LogicalForm(
            criterion_id=f"chia:{trial_id}:{idx}",
            source=Source.CHIA,
            polarity=Polarity.INCLUSION,  # TODO: inclusion/exclusion from the source file section
            text=ent.text,
            expression=expr,
            metadata={"trial_id": trial_id, "chia_tid": tid},
        ))
        idx += 1
    return forms
def load_chia_dir(root: str) -> list[LogicalForm]:
    """Load every .ann under `root`, pairing with .txt, into LogicalForm records."""
    forms: list[LogicalForm] = []
    for ann in sorted(Path(root).rglob("*.ann")):  # recursive: figshare extracts into subfolders
        doc = parse_ann(ann.read_text(encoding="utf-8", errors="ignore"))
        forms.extend(doc_to_logical_forms(doc, trial_id=ann.stem))
    return forms
