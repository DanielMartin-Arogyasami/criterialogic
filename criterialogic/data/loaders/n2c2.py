"""Load n2c2 2018 Track-1 records (DUA-gated) and align them to the criteria.
n2c2 is **not redistributable**. Obtain it under the Harvard DBMI DUA (see
`data/README.md`); place the XML files under `data/raw/n2c2_2018/`. This loader
reads the per-patient <TAGS> (met/not-met for each of the 13 criteria) and the
note text. The criterion *definitions* live in `data.n2c2_criteria` (public).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from criterialogic.data.n2c2_criteria import N2C2_TAGS

_MET_VALUES = {"met", "yes", "true", "1"}
class N2C2NotAvailable(FileNotFoundError):
    pass
def load_patient_labels(xml_path: str) -> dict[str, bool]:
    """Return {criterion_tag: met?} for one patient XML file."""
    tree = ET.parse(xml_path)
    tags_el = tree.getroot().find("TAGS")
    if tags_el is None:
        raise ValueError(f"No <TAGS> element in {xml_path}")
    labels: dict[str, bool] = {}
    for tag in N2C2_TAGS:
        el = tags_el.find(tag)
        if el is not None:
            labels[tag] = (el.get("met", "").strip().lower() in _MET_VALUES)
    return labels
def load_n2c2_dir(root: str = "data/raw/n2c2_2018") -> dict[str, dict[str, bool]]:
    """Return {record_id: {tag: met?}} for all patient files. Raises if DUA data absent."""
    p = Path(root)
    files = sorted(p.glob("*.xml"))
    if not files:
        raise N2C2NotAvailable(
            f"No n2c2 XML found under {root}. n2c2 is DUA-gated and never committed; "
            f"obtain it via the Harvard DBMI portal and see data/README.md."
        )
    return {f.stem: load_patient_labels(str(f)) for f in files}
