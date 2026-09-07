"""Two-annotator reliability workflow for the reasoning-failure taxonomy.

v0.1 had one annotator and compensated with a test-retest pass. v0.2 has two, and the
second is a design choice rather than a fallback: five of the seven categories —
negation/polarity, temporal, numeric threshold, logical composition, fabrication —
concern the structure of the criterion text, not its clinical content. Deciding whether
a model dropped a NOT or mis-scoped an OR is a linguistic and logical judgement.
Annotator 2 was selected for that. Only entity conflation and implicit-knowledge gap
need clinical knowledge, and the adjudication rule below says who governs there.

The workflow this module implements
-----------------------------------
1. :func:`sample_error_set` draws the annotation sample, stratified across models and
   nesting depths so the sample is not dominated by whichever run produced the most
   errors.
2. :func:`export_for_annotation` writes one CSV **per annotator**, containing the
   rendered criterion, the patient facts, gold, predicted, and confidence — and *not*
   the automatic label. Blind to the labeller and to each other by construction, not by
   instruction.
3. Both annotators fill ``category`` and tick ``clinical_judgement_required``.
4. :func:`agreement_report` computes Cohen's kappa with a bootstrap 95% interval,
   percent agreement, and a per-category breakdown, and slices all three:
   - by arm (compositional vs real criteria). The compositional arm has no clinical
     content, so agreement there measures whether the taxonomy itself is well defined.
     If agreement is high there and lower on real criteria, that locates where clinical
     knowledge is load-bearing — a finding, not a limitation.
   - by the ``clinical_judgement_required`` flag, with the flagged fraction reported.
5. :func:`disagreements` lists every disagreement for adjudication;
   :func:`load_adjudication` reads the resolutions back and
   :func:`consensus_labels` builds the final label set.
6. :func:`automatic_vs_consensus` reports the heuristic labeller as a third signal
   against the human consensus. It is a triage aid, not a gold standard, and is
   reported separately for that reason.

Whatever the agreement turns out to be is what gets published. A low kappa is a real
finding about how hard error attribution is, and the codebook revision history in
docs/CODEBOOK.md is the audit trail for how it was arrived at.

Everything is stdlib plus :mod:`criterialogic.metrics.stats`.
"""
from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

from criterialogic.metrics.stats import (
    cohens_kappa,
    kappa_with_ci,
    per_category_agreement,
    percent_agreement,
)
from criterialogic.models.llm_api import render_criterion, render_patient
from criterialogic.taxonomy.annotate import (
    LABELLER_VERSION,
    categorize_error,
    is_unanswerable,
)
from criterialogic.taxonomy.categories import FailureCategory

CATEGORY_VALUES = [c.value for c in FailureCategory]

#: Characters that make Excel, LibreOffice and Sheets treat a cell as a formula.
_FORMULA_LEADERS = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection in a cell.

    The annotation workflow has two people opening these CSVs in a spreadsheet, and the
    cells carry model-generated rationales and verbatim ClinicalTrials.gov text — neither
    of which this project controls. A rationale beginning ``=`` or ``@`` is evaluated as a
    formula on open, and the classic payloads (``=HYPERLINK``, ``=WEBSERVICE``, DDE via
    ``=cmd|``) exfiltrate or execute. Prefixing a single quote makes the cell literal text
    in every major spreadsheet, and leaves the value readable to the annotator.

    Applied on write, not on read, so an already-exported file stays valid and
    ``load_annotations`` strips the marker back off.
    """
    text = "" if value is None else str(value)
    if text.startswith(_FORMULA_LEADERS):
        return "'" + text
    return text


def _unquote(value: str) -> str:
    """Undo :func:`csv_safe` when reading an annotator's file back."""
    return value[1:] if value.startswith("'") else value

#: Columns the annotator fills. Kept to two: a category and one flag. Every extra field
#: is a chance for the two files to diverge in ways that are not disagreement.
ANNOTATOR_COLUMNS = ("category", "clinical_judgement_required", "notes")

#: What the annotator sees. `automatic_category` is deliberately absent.
EXPORT_COLUMNS = (
    "item_id", "arm", "model", "depth", "criterion", "polarity", "patient_facts",
    "gold", "predicted", "confidence", "model_rationale", *ANNOTATOR_COLUMNS,
)

#: Target sample size. 150 is the floor; 200 gives a kappa interval roughly +/-0.10 wide
#: at the agreement levels this task plausibly reaches.
TARGET_SAMPLE = 200
MINIMUM_SAMPLE = 150


# --------------------------------------------------------------------------- #
# Sampling
# --------------------------------------------------------------------------- #
def _error_rows(runs: dict, prompt_version: str = "2") -> list[dict]:
    """Flatten ``{label: (items, predictions)}`` into one row per error.

    ``prompt_version`` must match the renderer the evaluated run used. An annotator who
    is shown a different rendering of the record than the model saw is judging a
    different item — and for the currency defect (annotate.unanswerable_reasons) the two
    renderings differ on exactly the items most likely to be misattributed.
    """
    rows: list[dict] = []
    for label, (items, predictions) in runs.items():
        pred_by_id = {p.item_id: p for p in predictions}
        arm = items[0].task if items else "unknown"
        for item in items:
            pred = pred_by_id.get(item.item_id)
            if pred is None or pred.label == item.gold:
                continue
            rows.append({
                "item_id": item.item_id,
                "arm": arm,
                "model": label,
                "depth": item.depth if item.depth is not None else "",
                "criterion": render_criterion(item.criterion, prompt_version),
                "polarity": item.criterion.polarity.value,
                "patient_facts": render_patient(item.facts, prompt_version).replace("\n", " | "),
                "gold": "met" if item.gold else "not_met",
                "predicted": "met" if pred.label else "not_met",
                "confidence": f"{pred.confidence:.3f}",
                "model_rationale": (pred.rationale or "").replace("\n", " "),
                "_automatic_category": categorize_error(item, pred).value,
                "_unanswerable": "yes" if is_unanswerable(item, prompt_version) else "no",
            })
    return rows


def sample_error_set(runs: dict, n: int = TARGET_SAMPLE, seed: int = 11,
                     include_unanswerable: bool = False,
                     prompt_version: str = "2") -> list[dict]:
    """Draw a stratified random sample of errors across models and depths.

    Proportional allocation over (model, depth) strata, then random draw within each,
    so a run with 24 errors and a run with 3 both appear rather than the sample being
    whatever the largest run contributed. Deterministic in ``seed``.

    ``include_unanswerable`` defaults to False: items whose gold label rests on a fact
    the prompt never stated are renderer defects, and asking an annotator to attribute
    a reasoning failure to them wastes the scarcest resource in the project. They are
    counted and reported separately instead.

    ``prompt_version`` must match the run being annotated — pass ``"1"`` when annotating
    the v0.2 reported results.
    """
    rows = _error_rows(runs, prompt_version)
    if not include_unanswerable:
        rows = [r for r in rows if r["_unanswerable"] == "no"]
    if not rows:
        return []
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        strata[(r["model"], r["depth"])].append(r)
    rng = random.Random(seed)
    total = len(rows)
    target = min(n, total)
    picked: list[dict] = []
    for key in sorted(strata, key=lambda k: (str(k[0]), str(k[1]))):
        bucket = sorted(strata[key], key=lambda r: r["item_id"])
        take = max(1, round(target * len(bucket) / total))
        rng.shuffle(bucket)
        picked.extend(bucket[:take])
    rng.shuffle(picked)
    return picked[:target]


# --------------------------------------------------------------------------- #
# Export / import
# --------------------------------------------------------------------------- #
def export_for_annotation(sample: list[dict], out_dir: Path | str,
                          annotators: tuple[str, ...] = ("annotator1", "annotator2")) -> dict:
    """Write one blind CSV per annotator, plus a held-back file with the automatic labels.

    The annotator files carry no automatic category and no other annotator's labels. The
    held-back file exists so the third-signal comparison is possible later without ever
    having been visible during labelling.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name in annotators:
        path = out / f"errors_{name}.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(EXPORT_COLUMNS))
            w.writeheader()
            for row in sample:
                payload = {k: csv_safe(row.get(k, "")) for k in EXPORT_COLUMNS}
                payload.update({c: "" for c in ANNOTATOR_COLUMNS})
                w.writerow(payload)
        written.append(str(path))

    held = out / "automatic_labels_HELD_BACK.csv"
    with open(held, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "automatic_category",
                                           "unanswerable", "labeller_version"])
        w.writeheader()
        for row in sample:
            w.writerow({"item_id": csv_safe(row["item_id"]),
                        "automatic_category": row["_automatic_category"],
                        "unanswerable": row["_unanswerable"],
                        "labeller_version": LABELLER_VERSION})

    return {
        "annotator_files": written,
        "held_back_automatic_labels": str(held),
        "n_items": len(sample),
        "valid_categories": CATEGORY_VALUES,
        "meets_minimum": len(sample) >= MINIMUM_SAMPLE,
        "codebook": "docs/CODEBOOK.md",
    }


def load_annotations(path: Path | str) -> dict[str, dict]:
    """Read ``{item_id: {category, clinical_judgement_required, arm, depth, notes}}``.

    Rows with a blank category are skipped rather than defaulted, so a half-finished
    file produces a smaller n instead of a silently biased distribution. An unrecognised
    category is a hard error: a typo that becomes its own category would deflate kappa
    for a reason that has nothing to do with the taxonomy.
    """
    out: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = {"item_id", "category"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"{path}: missing required column(s) {sorted(missing)}. Found "
                f"{reader.fieldnames}. Re-export with scripts/annotation_export.py rather "
                f"than hand-building the file."
            )
        for row in reader:
            cat = _unquote((row.get("category") or "").strip()).lower()
            if not cat:
                continue
            if cat not in CATEGORY_VALUES:
                raise ValueError(
                    f"{path}: item {row.get('item_id')!r} has category {cat!r}, which is "
                    f"not one of {CATEGORY_VALUES}. Fix the cell rather than the checker."
                )
            flag = (row.get("clinical_judgement_required") or "").strip().lower()
            out[_unquote(row["item_id"])] = {
                "category": cat,
                "clinical_judgement_required": flag in ("y", "yes", "true", "1", "x"),
                "arm": (row.get("arm") or "").strip(),
                "depth": (row.get("depth") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
            }
    return out


# --------------------------------------------------------------------------- #
# Agreement
# --------------------------------------------------------------------------- #
def _aligned(a: dict[str, dict], b: dict[str, dict],
             predicate=None) -> tuple[list[str], list[str], list[str]]:
    ids = sorted(set(a) & set(b))
    if predicate is not None:
        ids = [i for i in ids if predicate(a[i], b[i])]
    return ids, [a[i]["category"] for i in ids], [b[i]["category"] for i in ids]


def _block(a: dict[str, dict], b: dict[str, dict], predicate=None,
           n_boot: int = 5000, seed: int = 0) -> dict:
    ids, la, lb = _aligned(a, b, predicate)
    if not ids:
        return {"n": 0, "kappa": None, "ci_95": (None, None), "percent_agreement": None}
    stats = kappa_with_ci(la, lb, n_boot=n_boot, seed=seed)
    stats["per_category"] = per_category_agreement(la, lb)
    stats["annotator1_distribution"] = dict(sorted(Counter(la).items()))
    stats["annotator2_distribution"] = dict(sorted(Counter(lb).items()))
    return stats


def agreement_report(a: dict[str, dict], b: dict[str, dict],
                     n_boot: int = 5000, seed: int = 0) -> dict:
    """Full agreement report: overall, by arm, and by clinical-judgement flag."""
    ids = sorted(set(a) & set(b))
    if not ids:
        raise ValueError("The two annotation files share no completed items.")

    flagged_ids = [i for i in ids
                   if a[i]["clinical_judgement_required"] or b[i]["clinical_judgement_required"]]
    arms = sorted({a[i]["arm"] for i in ids if a[i]["arm"]})

    report = {
        "n_shared_items": len(ids),
        "n_only_annotator1": len(set(a) - set(b)),
        "n_only_annotator2": len(set(b) - set(a)),
        "meets_minimum_sample": len(ids) >= MINIMUM_SAMPLE,
        "overall": _block(a, b, None, n_boot, seed),
        "by_arm": {
            arm: _block(a, b, lambda x, y, arm=arm: x["arm"] == arm, n_boot, seed)
            for arm in arms
        },
        "clinical_judgement": {
            "n_flagged": len(flagged_ids),
            "fraction_flagged": round(len(flagged_ids) / len(ids), 4),
            "flagged_by_annotator1": sum(1 for i in ids if a[i]["clinical_judgement_required"]),
            "flagged_by_annotator2": sum(1 for i in ids if b[i]["clinical_judgement_required"]),
            "flag_agreement": round(percent_agreement(
                ["y" if a[i]["clinical_judgement_required"] else "n" for i in ids],
                ["y" if b[i]["clinical_judgement_required"] else "n" for i in ids]), 4),
            "flagged": _block(a, b, lambda x, y: x["clinical_judgement_required"]
                              or y["clinical_judgement_required"], n_boot, seed),
            "not_flagged": _block(a, b, lambda x, y: not (x["clinical_judgement_required"]
                                  or y["clinical_judgement_required"]), n_boot, seed),
        },
        "by_depth": {},
    }
    depths = sorted({a[i]["depth"] for i in ids if a[i]["depth"]})
    for d in depths:
        report["by_depth"][d] = _block(a, b, lambda x, y, d=d: x["depth"] == d, n_boot, seed)
    return report


def disagreements(a: dict[str, dict], b: dict[str, dict]) -> list[dict]:
    """Every disagreement, for adjudication. All of them get resolved and recorded."""
    out = []
    for i in sorted(set(a) & set(b)):
        if a[i]["category"] == b[i]["category"]:
            continue
        clinical = a[i]["clinical_judgement_required"] or b[i]["clinical_judgement_required"]
        out.append({
            "item_id": i,
            "arm": a[i]["arm"],
            "depth": a[i]["depth"],
            "annotator1": a[i]["category"],
            "annotator2": b[i]["category"],
            "clinical_judgement_required": clinical,
            # Where the disagreement is clinical, annotator 1 governs and the paper says
            # so. Where it is linguistic or logical, it is resolved on the merits — the
            # second annotator was chosen for exactly that judgement, so overriding them
            # by default would discard the reason they are on the project.
            "adjudication_rule": "annotator1_governs" if clinical else "resolve_on_merits",
            "resolved_category": "",
            "resolution_note": "",
        })
    return out


def write_adjudication_sheet(rows: list[dict], path: Path | str) -> str:
    fields = ["item_id", "arm", "depth", "annotator1", "annotator2",
              "clinical_judgement_required", "adjudication_rule",
              "resolved_category", "resolution_note"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: csv_safe(r.get(k, "")) for k in fields})
    return str(path)


def load_adjudication(path: Path | str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cat = _unquote((row.get("resolved_category") or "").strip()).lower()
            if not cat:
                continue
            if cat not in CATEGORY_VALUES:
                raise ValueError(f"{path}: item {row.get('item_id')!r} resolved to {cat!r}, "
                                 f"which is not one of {CATEGORY_VALUES}.")
            out[_unquote(row["item_id"])] = {
                "category": cat,
                "note": (row.get("resolution_note") or "").strip()}
    return out


def consensus_labels(a: dict[str, dict], b: dict[str, dict],
                     adjudicated: dict[str, dict] | None = None) -> dict[str, str]:
    """Final labels: agreement where the annotators agreed, adjudication where they did not.

    Raises if a disagreement has no recorded resolution. Silently preferring one
    annotator would turn "every disagreement was adjudicated" into a claim the artifacts
    do not support.
    """
    adjudicated = adjudicated or {}
    out: dict[str, str] = {}
    unresolved: list[str] = []
    for i in sorted(set(a) & set(b)):
        if a[i]["category"] == b[i]["category"]:
            out[i] = a[i]["category"]
        elif i in adjudicated:
            out[i] = adjudicated[i]["category"]
        else:
            unresolved.append(i)
    if unresolved:
        raise ValueError(
            f"{len(unresolved)} disagreement(s) have no resolved_category, e.g. "
            f"{unresolved[:5]}. Adjudicate every one; the paper states that all were."
        )
    return out


def automatic_vs_consensus(consensus: dict[str, str],
                           automatic_csv: Path | str) -> dict:
    """The heuristic labeller as a third signal against the human consensus.

    Reported separately and never merged into the human distribution. Note that the
    labeller cannot assign entity conflation, implicit knowledge or fabrication, so
    those items are agreement-impossible by construction; the count is returned so a
    reader can see how much of any disagreement is structural.
    """
    auto: dict[str, str] = {}
    with open(automatic_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            auto[_unquote(row["item_id"])] = row["automatic_category"]
    ids = sorted(set(consensus) & set(auto))
    if not ids:
        return {"n": 0}
    human = [consensus[i] for i in ids]
    machine = [auto[i] for i in ids]
    from criterialogic.taxonomy.annotate import reachable_categories
    reachable = {c.value for c in reachable_categories()}
    impossible = sum(1 for h in human if h not in reachable)
    return {
        "n": len(ids),
        "labeller_version": LABELLER_VERSION,
        "kappa": round(cohens_kappa(human, machine), 4),
        "percent_agreement": round(percent_agreement(human, machine), 4),
        "n_agreement_impossible": impossible,
        "consensus_distribution": dict(sorted(Counter(human).items())),
        "automatic_distribution": dict(sorted(Counter(machine).items())),
        "note": "Triage aid, not a gold standard. Reported separately from the human labels.",
    }
