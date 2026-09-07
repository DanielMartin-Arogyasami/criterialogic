"""Arm 1 — real criteria, segmented from the snapshot and mapped onto the schema.

The compositional stress test (Arm 2) buys control over nesting depth at the cost of
clinical realism: real trials do not write depth-5 criteria. This module supplies the
other half of the pair — criteria exactly as trials wrote them, at whatever structure
they happen to have — so that a result on the stress test can be checked against
something that was not built to be hard.

Pipeline
--------
1. **Segment.** :func:`criterialogic.data.loaders.ctgov.iter_criterion_sentences`
   splits the ``eligibilityCriteria`` blob into ``(section, sentence)`` pairs, where
   section is ``inclusion`` or ``exclusion`` taken from the trial's own headers. No
   words are added, removed, or reordered.
2. **Map.** Each sentence becomes a :class:`LogicalForm` whose polarity is the section
   it came from and whose expression is built from the atom extractors already used
   for the pool, plus the conservative coordination rule below.
3. **Report.** Every sentence that does not map is counted by reason. The yield is a
   number the manuscript prints, not a detail the code hides.

Why polarity matters here
-------------------------
Every criterion in the v0.1 matching task was ``polarity=inclusion``, so criterion-level
polarity — the thing the schema goes out of its way to keep separate from logical
negation, and the first category in the failure taxonomy — was never exercised by any
released component. Real exclusion criteria fix that: the snapshot's exclusion sections
are the majority of what it yields.

Conservative by design
----------------------
A criterion is emitted only when the mapping is faithful to what it claims to represent:

* Coordination is handled only when **every** conjunct independently maps to an atom.
  "History of cardiac conduction disorders or documented arrhythmias" yields
  ``OR(conduction disorders, arrhythmias)``. "Cardiac, pulmonary, renal, or metabolic
  comorbidities" yields nothing, because clipping at the first comma would mint a
  criterion the trial did not write.
* A sentence mixing "and" with "or" is rejected outright: "A and B or C" has two readings
  and picking one assigns a structure the trial did not commit to.
* A sentence containing an un-comma'd "and" whose coordination mapping *fails* is also
  rejected. This is the important one. "Participants must have BMI >= 18 and <= 40" splits
  into a part that maps (``bmi >= 18``) and a part that does not (``<= 40``), and the
  single-atom fallback would emit ``bmi >= 18`` — a criterion that admits a patient with
  BMI 45 whom the trial excludes. Dropping a conjunct from a conjunction weakens it and
  flips gold labels toward "met", so the sentence is counted as unmapped instead.
* An explicit negation cue in the sentence wraps the expression in ``Not``. The cue set is
  small and literal; anything ambiguous is skipped rather than guessed.
* Sentences the atom extractors reject are skipped, counted, and never coerced.

What the expression is, and is not
----------------------------------
**The expression is a faithful sub-reading of the source sentence, not a complete
translation of it.** The underlying extractors were built to mine *predicates* for the
atom pool, where partiality is harmless because the stress test supplies its own
structure. Reused at criterion level, that partiality is inherited: "Patients aged 19 to
79 years undergoing elective non-cardiac surgery expected to last 60 minutes or longer"
maps to ``age between 19 and 79`` and drops the surgical requirement. Every form therefore
records ``metadata["coverage"] = "partial_predicate"``, and Arm 1 should be described as
testing decisions over *a real predicate drawn from real criterion text with the real
polarity of its section* — not as testing whole-criterion semantics. Whole-sentence
translation is a structuring task, and structuring is deferred (docs/V2_SCOPE.md).

The consequence for interpretation: Arm 1 validates that a system handles real clinical
vocabulary, real numeric and temporal qualifiers, and real inclusion/exclusion polarity.
It does not validate performance on the full logical structure of real criteria, and it
cannot, because that structure is mostly not recovered. Nearly all Arm 1 forms are
single-predicate (depth 0); the depth histogram reports exactly how few are not.

The result is high precision and low recall. That is the right trade for a gold set: a
mislabelled item is scored as a model failure, which is worse than a smaller *n*. Section
3 of the manuscript reports the recall figure so the reader can see what is being traded.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from criterialogic.data.loaders.ctgov import (
    _STOP_PHRASES,
    DEFAULT_CACHE,
    MAX_SENTENCE_CHARS,
    MIN_SENTENCE_CHARS,
    _sentence_to_atom,
    eligibility_text,
    first_posted,
    iter_criterion_sentences,
    load_cached_studies,
    nct_id,
    read_manifest,
)
from criterialogic.schema.logical_form import (
    BooleanGroup,
    BoolOp,
    Expression,
    LogicalForm,
    Not,
    Polarity,
    Source,
)

#: Literal negation cues. Kept small on purpose: a cue list that tries to cover every
#: phrasing starts silently negating criteria it has misread, and a flipped polarity is
#: exactly the error the benchmark is built to detect.
_NEGATION_CUES = (
    r"^no\s+(?:history\s+of\s+|known\s+|evidence\s+of\s+|prior\s+|current\s+)?",
    r"^absence\s+of\s+",
    r"^without\s+",
    r"^free\s+of\s+",
    r"^not\s+(?:receiving|taking|treated\s+with|currently)\s+",
)
_NEGATION_RE = re.compile("|".join(_NEGATION_CUES), re.IGNORECASE)

#: Splits a coordinated phrase on a top-level "or"/"and". Applied only to sentences with
#: no comma enumeration, and only accepted when every part maps to an atom.
_COORD_SPLIT_RE = re.compile(r"\s+(?:or|and)\s+", re.IGNORECASE)

MAX_COORDINATION_PARTS = 3


@dataclass
class SegmentationStats:
    """Counts needed to report yield honestly rather than only the criteria that worked."""

    studies: int = 0
    sentences: int = 0
    mapped_single_atom: int = 0
    mapped_coordinated: int = 0
    negated: int = 0
    skipped: dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    @property
    def mapped(self) -> int:
        return self.mapped_single_atom + self.mapped_coordinated

    def to_json(self) -> dict:
        total = self.sentences or 1
        return {
            "studies": self.studies,
            "sentences_considered": self.sentences,
            "criteria_mapped": self.mapped,
            "criteria_mapped_single_atom": self.mapped_single_atom,
            "criteria_mapped_coordinated": self.mapped_coordinated,
            "criteria_negated": self.negated,
            "mapping_rate": round(self.mapped / total, 4),
            "sentences_skipped": sum(self.skipped.values()),
            "skipped_by_reason": dict(sorted(self.skipped.items())),
        }


def _strip_negation_cue(sentence: str) -> tuple[str, bool]:
    """Remove a leading negation cue, returning the remainder and whether one fired."""
    m = _NEGATION_RE.match(sentence)
    if not m:
        return sentence, False
    return sentence[m.end():].strip(), True


def _coordinated_expression(sentence: str) -> tuple[Expression, str] | None:
    """Build an n-ary group when every conjunct independently maps to an atom.

    Returns ``None`` — not a partial group — if any part fails, because a group missing
    one of its operands is a different criterion from the one the trial wrote.
    """
    if "," in sentence:
        return None  # enumerations are handled by rejection, see module docstring
    has_or = re.search(r"\s+or\s+", sentence, re.IGNORECASE) is not None
    has_and = re.search(r"\s+and\s+", sentence, re.IGNORECASE) is not None
    if has_or and has_and:
        # "A and B or C" has two readings — (A and B) or C, and A and (B or C) — and
        # picking one would assign a criterion a structure the trial did not commit to.
        # Rejecting is the only faithful option; the sentence is counted as unmapped.
        return None
    parts = [p.strip() for p in _COORD_SPLIT_RE.split(sentence) if p.strip()]
    if not 2 <= len(parts) <= MAX_COORDINATION_PARTS:
        return None
    operator = BoolOp.OR if has_or else BoolOp.AND
    atoms: list[Expression] = []
    for part in parts:
        hit = _sentence_to_atom(part)
        if hit is None:
            return None
        atoms.append(hit[0])
    # Distinct entities only: "diabetes or diabetes" is a extraction artefact, not an OR.
    if len({a.model_dump_json() for a in atoms}) < len(atoms):
        return None
    return BooleanGroup(operator=operator, operands=atoms), f"coordinated_{operator.value}"


def sentence_to_expression(sentence: str) -> tuple[Expression, str, bool] | None:
    """Map one criterion sentence to an expression.

    Returns ``(expression, rule, negated)`` or ``None`` when the sentence cannot be
    mapped faithfully.
    """
    body, negated = _strip_negation_cue(sentence)
    if not body:
        return None
    coordinated = _coordinated_expression(body)
    if coordinated is not None:
        expr, rule = coordinated
    else:
        if _has_unmapped_conjunction(body):
            # Falling back to a single atom here would drop a conjunct and weaken the
            # criterion. See the module docstring: this is the BMI >= 18 and <= 40 case.
            return None
        hit = _sentence_to_atom(body)
        if hit is None:
            return None
        expr, rule = hit[0], hit[1]
    if negated:
        expr = Not(operand=expr)
    return expr, rule, negated


def _has_unmapped_conjunction(sentence: str) -> bool:
    """True when the sentence conjoins requirements that the single-atom path would drop."""
    return "," not in sentence and re.search(r"\s+and\s+", sentence, re.IGNORECASE) is not None


def build_criterion_forms(
    cache_dir: Path | str | None = None,
    max_per_study: int | None = 4,
    limit: int | None = None,
) -> tuple[list[LogicalForm], SegmentationStats]:
    """Segment every cached study into LogicalForms. Deterministic: no sampling.

    ``max_per_study`` caps how many criteria any single trial contributes, so a trial
    with a 40-bullet exclusion list does not dominate the set. ``limit`` truncates the
    result for smoke tests; leave it ``None`` for the released set.
    """
    cache_dir = DEFAULT_CACHE if cache_dir is None else cache_dir
    studies = load_cached_studies(cache_dir)
    manifest = read_manifest(cache_dir) or {}
    snapshot_id = manifest.get("snapshot_id", "ctgov-unknown")
    stats = SegmentationStats()
    forms: list[LogicalForm] = []
    seen: set[str] = set()

    for study in sorted(studies, key=lambda s: nct_id(s) or ""):
        nct = nct_id(study)
        if not nct:
            continue
        stats.studies += 1
        posted = first_posted(study)
        kept = 0
        for section, sentence in iter_criterion_sentences(eligibility_text(study)):
            stats.sentences += 1
            if not MIN_SENTENCE_CHARS <= len(sentence) <= MAX_SENTENCE_CHARS:
                stats.skip("length_out_of_range")
                continue
            low = sentence.lower()
            if any(sp in low for sp in _STOP_PHRASES):
                stats.skip("boilerplate_phrase")
                continue
            try:
                mapped = sentence_to_expression(sentence)
            except ValueError:
                # A schema validator rejected the constraint. Skipping is correct: the
                # alternative is inventing a plausible bound.
                stats.skip("schema_rejected_constraint")
                continue
            if mapped is None:
                stats.skip("no_faithful_mapping")
                continue
            expr, rule, negated = mapped
            key = f"{section}|{expr.model_dump_json()}"
            if key in seen:
                stats.skip("duplicate_of_earlier_trial")
                continue
            seen.add(key)
            if isinstance(expr, BooleanGroup) or (isinstance(expr, Not)
                                                  and isinstance(expr.operand, BooleanGroup)):
                stats.mapped_coordinated += 1
            else:
                stats.mapped_single_atom += 1
            if negated:
                stats.negated += 1
            forms.append(LogicalForm(
                criterion_id=f"ctgov:{nct}:{section[:3]}:{kept:02d}",
                source=Source.CTGOV,
                polarity=Polarity.EXCLUSION if section == "exclusion" else Polarity.INCLUSION,
                text=sentence,
                expression=expr,
                metadata={
                    "trial_id": nct,
                    "section": section,
                    "first_posted": posted or "",
                    "extraction_rule": rule,
                    "snapshot_id": snapshot_id,
                    "explicit_negation_cue": "yes" if negated else "no",
                    # The expression is a faithful sub-reading of `text`, not a complete
                    # translation of it. See the module docstring.
                    "coverage": "partial_predicate",
                },
            ))
            kept += 1
            if max_per_study is not None and kept >= max_per_study:
                break
        if limit is not None and len(forms) >= limit:
            break
    if limit is not None:
        forms = forms[:limit]
    return forms, stats


def polarity_distribution(forms: list[LogicalForm]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in forms:
        out[f.polarity.value] = out.get(f.polarity.value, 0) + 1
    return out


def structure_distribution(forms: list[LogicalForm]) -> dict[str, int]:
    """Depth histogram — the honest counterweight to the stress test.

    Real criteria are overwhelmingly shallow. Printing this next to the depth-stratified
    stress-test results is what keeps the paper from implying that depth-5 criteria are
    a common thing a screening system meets in the wild.
    """
    from criterialogic.tasks.base import expression_depth

    out: dict[str, int] = {}
    for f in forms:
        d = str(expression_depth(f.expression))
        out[d] = out.get(d, 0) + 1
    return dict(sorted(out.items()))
