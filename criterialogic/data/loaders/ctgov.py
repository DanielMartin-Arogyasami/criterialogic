"""ClinicalTrials.gov API v2 adapter — the real source of the Task-D atom pool.

Two responsibilities, deliberately separated:

*Acquisition* — :func:`fetch_studies` walks the public v2 REST API and caches each
study's raw JSON under ``data/ctgov_cache/<NCT_ID>.json``. Pagination is cursor-based
(``nextPageToken``); the retired v1 API and its ``min_rnk``/``max_rnk`` paging do not
exist any more and are not implemented here. Requests are rate-limited and a cached
study is never re-fetched.

*Extraction* — :func:`extract_atoms` turns the free-text ``eligibilityCriteria`` blob
into :class:`Atom` objects. This is a deliberately conservative, fully deterministic
rule-based extractor, not a claim about NLP quality: a sentence is either matched by
one of the patterns in ``_PATTERNS`` or it is skipped and counted as unmapped. Nothing
is coerced into an atom to raise the yield. Every atom it emits carries the NCT ID and
the verbatim sentence it came from, so any downstream item resolves back to source text.

The data is US Government public-domain and needs no DUA, but it is fetched over the
network: the cache is what makes offline and CI runs possible.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from criterialogic.schema.logical_form import (
    Atom,
    Comparator,
    Entity,
    EntityType,
    NumericConstraint,
    TemporalConstraint,
    TemporalOp,
    TimeUnit,
)

API_BASE = "https://clinicaltrials.gov/api/v2"
STUDIES_URL = f"{API_BASE}/studies"
DEFAULT_CACHE = Path("data/ctgov_cache")
MANIFEST_NAME = "MANIFEST.json"

#: Field paths requested from the API. Keeping this narrow keeps cached records small
#: enough to check a fixture into version control.
FIELDS = (
    "protocolSection.identificationModule.nctId",
    "protocolSection.identificationModule.briefTitle",
    "protocolSection.statusModule.studyFirstPostDateStruct",
    "protocolSection.designModule.studyType",
    "protocolSection.designModule.phases",
    "protocolSection.eligibilityModule.eligibilityCriteria",
)

#: At most 2 requests/second against the public API.
MIN_REQUEST_INTERVAL_S = 0.5

_USER_AGENT = "CriteriaLogic/0.1 (+https://github.com/USERNAME/criterialogic)"

#: Bumped whenever the extraction rules change, so a pool file built by an older
#: version is identifiable rather than silently mixed with a newer one.
EXTRACTOR_VERSION = "1"


class CTGovError(RuntimeError):
    """Base class for ClinicalTrials.gov acquisition failures."""


class CTGovUnavailable(CTGovError):
    """The API could not be reached. Never downgrade this to a synthetic fallback."""


# --------------------------------------------------------------------------- #
# Query specification
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StudyQuery:
    """The sampling frame, recorded verbatim into the cache manifest.

    Phase-IV interventional studies mirror Chia's frame. ``first_posted_from`` exists
    for the contamination argument: restricting to trials first posted after a model's
    training cutoff is what turns "probably unseen" into evidence.
    """

    phase: str = "PHASE4"
    study_type: str = "INTERVENTIONAL"
    first_posted_from: str | None = None  # ISO date, e.g. "2025-07-01"
    sort: str = "StudyFirstPostDate:desc"
    page_size: int = 100

    def advanced_expression(self) -> str:
        parts = [f"AREA[Phase]{self.phase}", f"AREA[StudyType]{self.study_type}"]
        if self.first_posted_from:
            parts.append(f"AREA[StudyFirstPostDate]RANGE[{self.first_posted_from},MAX]")
        return " AND ".join(parts)

    def as_params(self) -> dict[str, str]:
        return {
            "filter.advanced": self.advanced_expression(),
            "fields": ",".join(FIELDS),
            "sort": self.sort,
            "pageSize": str(self.page_size),
            "countTotal": "true",
        }


# --------------------------------------------------------------------------- #
# HTTP with rate limiting
# --------------------------------------------------------------------------- #
class RateLimiter:
    """Blocks so that successive calls are >= ``interval`` apart."""

    def __init__(self, interval: float = MIN_REQUEST_INTERVAL_S,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.interval = interval
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last is not None:
            remaining = self.interval - (now - self._last)
            if remaining > 0:
                self._sleep(remaining)
                now = self._clock()
        self._last = now


def _http_json(url: str, timeout: int = 60) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:  # pragma: no cover - network dependent
        raise CTGovError(f"ClinicalTrials.gov returned HTTP {e.code} for {url}: {e.reason}") from e
    except urllib.error.URLError as e:  # pragma: no cover - network dependent
        raise CTGovUnavailable(
            f"Could not reach {url} ({e.reason}). ClinicalTrials.gov v2 is a public API; "
            f"check network access. Do not substitute synthetic criteria."
        ) from e


# --------------------------------------------------------------------------- #
# Record accessors — every field is optional in the API response
# --------------------------------------------------------------------------- #
def _section(study: dict, *path: str) -> Any:
    node: Any = study.get("protocolSection", {})
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def nct_id(study: dict) -> str | None:
    return _section(study, "identificationModule", "nctId")


def eligibility_text(study: dict) -> str:
    return _section(study, "eligibilityModule", "eligibilityCriteria") or ""


def first_posted(study: dict) -> str | None:
    return _section(study, "statusModule", "studyFirstPostDateStruct", "date")


def brief_title(study: dict) -> str | None:
    return _section(study, "identificationModule", "briefTitle")


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #
def cache_path(nct: str, cache_dir: Path | str = DEFAULT_CACHE) -> Path:
    return Path(cache_dir) / f"{nct}.json"


def load_cached_study(nct: str, cache_dir: Path | str = DEFAULT_CACHE) -> dict | None:
    p = cache_path(nct, cache_dir)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_cached_studies(cache_dir: Path | str = DEFAULT_CACHE) -> list[dict]:
    """Every cached study, ordered by NCT ID so downstream output is deterministic."""
    d = Path(cache_dir)
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("NCT*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def _write_cache(study: dict, cache_dir: Path) -> None:
    nct = nct_id(study)
    if not nct:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path(nct, cache_dir).write_text(
        json.dumps(study, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_manifest(cache_dir: Path | str, query: StudyQuery, n_studies: int,
                   pages: int, fetched_utc: str) -> Path:
    """Record the exact query that produced the cache, so the frame is auditable."""
    d = Path(cache_dir)
    d.mkdir(parents=True, exist_ok=True)
    manifest = {
        "api_base": API_BASE,
        "query_params": query.as_params(),
        "advanced_expression": query.advanced_expression(),
        "fields": list(FIELDS),
        "first_posted_from": query.first_posted_from,
        "n_studies_cached": n_studies,
        "pages_fetched": pages,
        "fetched_utc": fetched_utc,
        "rate_limit_requests_per_second": round(1.0 / MIN_REQUEST_INTERVAL_S, 3),
    }
    p = d / MANIFEST_NAME
    p.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return p


def read_manifest(cache_dir: Path | str = DEFAULT_CACHE) -> dict | None:
    p = Path(cache_dir) / MANIFEST_NAME
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


# --------------------------------------------------------------------------- #
# Acquisition
# --------------------------------------------------------------------------- #
def iter_studies(query: StudyQuery, limit: int,
                 limiter: RateLimiter | None = None) -> Iterator[dict]:
    """Yield study records, following ``nextPageToken`` until ``limit`` is reached."""
    limiter = limiter or RateLimiter()
    params = query.as_params()
    token: str | None = None
    yielded = 0
    while yielded < limit:
        page_params = dict(params)
        page_params["pageSize"] = str(min(query.page_size, limit - yielded))
        if token:
            page_params["pageToken"] = token
        limiter.wait()
        payload = _http_json(f"{STUDIES_URL}?{urllib.parse.urlencode(page_params)}")
        studies = payload.get("studies") or []
        if not studies:
            return
        for study in studies:
            yield study
            yielded += 1
            if yielded >= limit:
                return
        token = payload.get("nextPageToken")
        if not token:
            return


def fetch_studies(query: StudyQuery | None = None, limit: int = 100,
                  cache_dir: Path | str = DEFAULT_CACHE,
                  limiter: RateLimiter | None = None) -> dict:
    """Populate the cache with up to ``limit`` studies matching ``query``.

    Studies already cached are kept as-is and never re-fetched; the fetch tops the cache
    up to ``limit`` records rather than replacing it.
    """
    query = query or StudyQuery()
    cache = Path(cache_dir)
    existing = {p.stem for p in cache.glob("NCT*.json")} if cache.is_dir() else set()
    needed = max(0, limit - len(existing))
    fetched_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new = 0
    if needed:
        # Over-request so that already-cached hits do not eat into the new-record budget.
        for study in iter_studies(query, limit=limit, limiter=limiter):
            nct = nct_id(study)
            if not nct or nct in existing:
                continue
            _write_cache(study, cache)
            existing.add(nct)
            new += 1
            if new >= needed:
                break
    total = len({p.stem for p in cache.glob("NCT*.json")}) if cache.is_dir() else 0
    write_manifest(cache, query, n_studies=total, pages=0, fetched_utc=fetched_utc)
    return {"cached_total": total, "newly_fetched": new,
            "cache_dir": str(cache), "fetched_utc": fetched_utc}


def fetch_eligibility(nct_ids: list[str], cache_dir: Path | str = DEFAULT_CACHE,
                      limiter: RateLimiter | None = None) -> dict[str, str]:
    """Return ``{nct_id: eligibility_text}``, serving cache hits without a request."""
    limiter = limiter or RateLimiter()
    cache = Path(cache_dir)
    out: dict[str, str] = {}
    for nct in nct_ids:
        study = load_cached_study(nct, cache)
        if study is None:
            limiter.wait()
            url = f"{STUDIES_URL}/{urllib.parse.quote(nct)}?{urllib.parse.urlencode({'fields': ','.join(FIELDS)})}"
            study = _http_json(url)
            _write_cache(study, cache)
        out[nct] = eligibility_text(study)
    return out


def search_trials(query: str, page_size: int = 20) -> list[str]:
    """Free-text search returning NCT IDs. Retained for `scripts/download_data.py`."""
    params = urllib.parse.urlencode({
        "query.term": query,
        "pageSize": page_size,
        "fields": "protocolSection.identificationModule.nctId",
    })
    payload = _http_json(f"{STUDIES_URL}?{params}")
    return [n for n in (nct_id(s) for s in payload.get("studies") or []) if n]


# --------------------------------------------------------------------------- #
# Extraction: eligibility prose -> atoms
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AtomRecord:
    """One atom plus everything needed to trace it back to its source trial."""

    atom: Atom
    nct_id: str
    sentence: str  # verbatim, as it appears in the eligibility blob
    section: str  # "inclusion" | "exclusion"
    first_posted: str | None
    fetched_utc: str
    pattern: str  # which extraction rule fired

    def to_json(self) -> dict:
        return {
            "atom": self.atom.model_dump(mode="json"),
            "nct_id": self.nct_id,
            "sentence": self.sentence,
            "section": self.section,
            "first_posted": self.first_posted,
            "fetched_utc": self.fetched_utc,
            "pattern": self.pattern,
        }


@dataclass
class ExtractionStats:
    """Counts needed to report yield honestly rather than only the atoms that worked."""

    studies: int = 0
    sentences: int = 0
    matched: int = 0
    unmapped_reasons: dict[str, int] = field(default_factory=dict)
    patterns: dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str) -> None:
        self.unmapped_reasons[reason] = self.unmapped_reasons.get(reason, 0) + 1

    def hit(self, pattern: str) -> None:
        self.patterns[pattern] = self.patterns.get(pattern, 0) + 1

    def to_json(self) -> dict:
        return {
            "studies": self.studies,
            "sentences_considered": self.sentences,
            "sentences_matched": self.matched,
            "sentences_unmapped": sum(self.unmapped_reasons.values()),
            "unmapped_by_reason": dict(sorted(self.unmapped_reasons.items())),
            "matched_by_pattern": dict(sorted(self.patterns.items())),
        }


_HEADER_RE = re.compile(r"^\s*(inclusion|exclusion)\s+criteria\b\s*:?\s*$", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*(?:[-*\u2022\u00b7]|\(?\d+\\?[.)])\s*")
_WS_RE = re.compile(r"\s+")
#: ClinicalTrials.gov ships eligibility text with markdown-style backslash escapes
#: ("6\. History of ...", "platelet count \<150"). They are display artifacts.
_ESCAPE_RE = re.compile(r"\\([^A-Za-z0-9\s])")
#: A comma-separated list closed by "or"/"and" — a coordinated set, not one predicate.
_ENUMERATION_RE = re.compile(r",\s*(?:[^,]{1,40}\s+)?(?:or|and)\s+", re.IGNORECASE)
#: A bound written into the phrase itself belongs in a NumericConstraint, not in the
#: entity text; an atom carrying "<250 um" in its name is opaque to the evaluator.
_INLINE_BOUND_RE = re.compile(r"[<>≤≥]|\b\d+\s*(?:%|mg|ml|kg|g/l|mmhg|um|µm)\b", re.IGNORECASE)
#: Interventions the "use of"/"treatment with" cues would otherwise mistype as drugs.
_PROCEDURE_SUFFIXES = (
    "management", "monitoring", "surgery", "resection", "fixation", "biopsy",
    "transplantation", "dissection", "catheterization", "ventilation", "dialysis",
    "intubation", "endoscopy", "imaging", "screening",
)

MIN_SENTENCE_CHARS = 12
MAX_SENTENCE_CHARS = 180
MAX_ENTITY_WORDS = 6

_UNITS = {"day": TimeUnit.DAYS, "days": TimeUnit.DAYS, "week": TimeUnit.WEEKS,
          "weeks": TimeUnit.WEEKS, "month": TimeUnit.MONTHS, "months": TimeUnit.MONTHS,
          "year": TimeUnit.YEARS, "years": TimeUnit.YEARS}

#: Measurements the extractor is willing to attach a numeric constraint to. A numeric
#: bound on anything outside this lexicon is dropped rather than guessed at, because the
#: schema forbids numeric constraints on non-measurable entity types. Units are read
#: from the source text, never supplied from this list — trials report the same analyte
#: in different units and substituting a canonical one would fabricate the threshold.
_MEASUREMENTS = (
    "hba1c", "a1c", "bmi", "body mass index", "egfr", "creatinine", "hemoglobin",
    "haemoglobin", "platelet count", "platelets", "ldl", "ldl-c", "hdl", "triglycerides",
    "systolic blood pressure", "diastolic blood pressure", "ejection fraction", "weight",
    "alt", "ast", "bilirubin", "fasting plasma glucose", "fasting blood glucose",
)

#: A bound stated relative to a reference range ("<= 3 times ULN") is not an absolute
#: value; recording the bare number would misstate the threshold, so the atom is skipped.
_RELATIVE_BOUND_RE = re.compile(r"^\s*(?:times|x|×|\*)?\s*(?:the\s+)?"
                                r"(?:uln|lln|upper limit|lower limit)", re.IGNORECASE)

_UNIT_RE = re.compile(r"^\s*([%A-Za-zµμ][A-Za-z0-9µμ%^/·\.\-²³]{0,14})")

_COMPARATORS = {
    "<": Comparator.LT, "≤": Comparator.LE, "<=": Comparator.LE,
    ">": Comparator.GT, "≥": Comparator.GE, ">=": Comparator.GE,
}

_DRUG_CUES = ("treatment with", "therapy with", "use of", "receiving", "taking", "treated with")
_CONDITION_CUES = ("history of", "diagnosis of", "diagnosed with", "patients with",
                   "presence of", "known", "documented", "confirmed")

_STOP_PHRASES = (
    "informed consent", "written consent", "able to", "willing to", "willingness",
    "in the opinion of the investigator", "per investigator", "any other",
    "as determined by", "participants who", "subjects who", "patients who",
)


def _normalize_ws(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _clean_phrase(phrase: str) -> str | None:
    """Trim a captured phrase to a concise concept, or reject it.

    A coordinated phrase ("oral or intravenous antibiotics") is *rejected*, not truncated
    to its first conjunct. Truncating would mint an atom that misrepresents the source
    sentence, which is worse than a lower yield: the point of this pool is that every atom
    faithfully reflects real trial text.
    """
    p = re.sub(r"\([^)]*\)", " ", phrase)  # drop parentheticals, keep the head noun after them
    p = _normalize_ws(p)
    # Drop clause tails; any temporal content is captured separately by _temporal_from.
    p = re.split(r"[,;:\[]", p, maxsplit=1)[0]
    p = re.split(r"\s+(?:prior to|within|before|after|during|at screening|at baseline"
                 r"|in the past|who|which|that|whose)\b", p, maxsplit=1, flags=re.IGNORECASE)[0]
    prev = None
    while prev != p:
        prev = p
        p = re.sub(r"^\s*(?:a|an|the|any|all|other|current|currently|ongoing|active|known"
                   r"|suspected|prior|previous|recent|past|planned|or|and|of|to|with)\s+",
                   "", p, flags=re.IGNORECASE)
        p = re.sub(r"\s+(?:such|including|include|e\.?g\.?|i\.?e\.?|with|of|to|in|at|for|from"
                   r"|by|than|and|or|as|the|a|an|currently|recently|previously|prior"
                   r"|regularly|now)\s*$", "", p, flags=re.IGNORECASE)
        p = p.strip(" ,.;:()[]-")
    p = p.lower()
    if not p or not re.search(r"[a-z]", p):
        return None
    if re.search(r"\s+(?:and|or)\s+", p):
        return None  # coordinated: two predicates, not one atom
    if _INLINE_BOUND_RE.search(p):
        return None
    if len(p.split()) > MAX_ENTITY_WORDS or len(p) < 3:
        return None
    return p


def _measurement_key(text: str) -> str | None:
    low = text.lower()
    # Longest match first so "systolic blood pressure" beats a bare substring.
    for name in sorted(_MEASUREMENTS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", low):
            return name
    return None


def _unit_after(text: str, pos: int) -> str | None:
    """Read the unit that follows a numeric bound, verbatim. None if none is stated."""
    tail = text[pos:]
    if _RELATIVE_BOUND_RE.match(tail):
        return _RELATIVE_BOUND
    m = _UNIT_RE.match(tail)
    if not m:
        return None
    unit = m.group(1).strip(" .,;:")
    if not unit or unit.lower() in _UNIT_STOPWORDS:
        return None
    return unit


_RELATIVE_BOUND = "\x00relative"  # sentinel: caller must discard the atom
_UNIT_STOPWORDS = {
    "and", "or", "at", "in", "on", "of", "to", "the", "a", "an", "for", "with", "per",
    "times", "x", "within", "before", "after", "who", "if", "as", "is", "are", "was",
}


def _temporal_from(sentence: str) -> TemporalConstraint | None:
    m = re.search(r"\bwithin\s+(?:the\s+)?(?:past|last|previous\s+)?\s*(\d+)\s*"
                  r"(day|days|week|weeks|month|months|year|years)\b", sentence, re.IGNORECASE)
    if m:
        return TemporalConstraint(operator=TemporalOp.WITHIN, value=float(m.group(1)),
                                  unit=_UNITS[m.group(2).lower()], anchor="enrollment")
    m = re.search(r"\bfor\s+at\s+least\s+(\d+)\s*"
                  r"(day|days|week|weeks|month|months|year|years)\b", sentence, re.IGNORECASE)
    if m:
        return TemporalConstraint(operator=TemporalOp.FOR_AT_LEAST, value=float(m.group(1)),
                                  unit=_UNITS[m.group(2).lower()], anchor="enrollment")
    if re.search(r"\bhistory of\b|\bever\b|\bprevious(?:ly)?\b|\bprior\b", sentence, re.IGNORECASE):
        return TemporalConstraint(operator=TemporalOp.ANY_HISTORY)
    if re.search(r"\bcurrent(?:ly)?\b|\bongoing\b|\bactive\b", sentence, re.IGNORECASE):
        return TemporalConstraint(operator=TemporalOp.CURRENT)
    return None


def _age_atom(sentence: str) -> tuple[Atom, str] | None:
    s = sentence.lower()
    m = re.search(r"\bages?d?\s*(?:between\s+)?(\d{1,3})\s*(?:-|–|to|and)\s*(\d{1,3})\s*years?\b", s)
    if not m:
        m = re.search(r"\b(\d{1,3})\s*(?:-|–|to)\s*(\d{1,3})\s*years?\s*(?:of age|old)\b", s)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if hi > lo:
            return Atom(entity=Entity(text="age", type=EntityType.PERSON),
                        numeric=NumericConstraint(operator=Comparator.BETWEEN, value=lo,
                                                  upper=hi, unit="years")), "age_range"
    m = re.search(r"\b(?:age[d]?\s*)?(\d{1,3})\s*years?\s*(?:of age\s*)?(?:or older|and older|and above)\b", s)
    if not m:
        m = re.search(r"\bage[d]?\s*(?:>=|≥|at least|greater than or equal to|older than|over)\s*(\d{1,3})\b", s)
    if m:
        return Atom(entity=Entity(text="age", type=EntityType.PERSON),
                    numeric=NumericConstraint(operator=Comparator.GE, value=float(m.group(1)),
                                              unit="years")), "age_min"
    m = re.search(r"\bage[d]?\s*(?:<=|≤|at most|less than or equal to|younger than|under)\s*(\d{1,3})\b", s)
    if m:
        return Atom(entity=Entity(text="age", type=EntityType.PERSON),
                    numeric=NumericConstraint(operator=Comparator.LE, value=float(m.group(1)),
                                              unit="years")), "age_max"
    return None


def _measurement_atom(sentence: str) -> tuple[Atom, str] | None:
    name = _measurement_key(sentence)
    if not name:
        return None
    pattern = rf"\b{re.escape(name)}\b[^0-9<>≤≥]{{0,24}}?(<=|>=|≤|≥|<|>)\s*([0-9]+(?:\.[0-9]+)?)"
    m = re.search(pattern, sentence, re.IGNORECASE)
    if m:
        unit = _unit_after(sentence, m.end())
        if unit is _RELATIVE_BOUND:
            return None
        return Atom(
            entity=Entity(text=name, type=EntityType.MEASUREMENT),
            numeric=NumericConstraint(operator=_COMPARATORS[m.group(1)], value=float(m.group(2)),
                                      unit=unit),
        ), "measurement_threshold"
    m = re.search(rf"\b{re.escape(name)}\b[^0-9]{{0,24}}?between\s+([0-9.]+)\s+and\s+([0-9.]+)",
                  sentence, re.IGNORECASE)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        unit = _unit_after(sentence, m.end())
        if unit is _RELATIVE_BOUND:
            return None
        if hi > lo:
            return Atom(
                entity=Entity(text=name, type=EntityType.MEASUREMENT),
                numeric=NumericConstraint(operator=Comparator.BETWEEN, value=lo, upper=hi,
                                          unit=unit),
            ), "measurement_range"
    return None


def _cued_concept_atom(sentence: str) -> tuple[Atom, str] | None:
    """Concept introduced by an explicit lexical cue, e.g. 'history of <X>'."""
    if _ENUMERATION_RE.search(sentence):
        # "cardiac, pulmonary, renal, or metabolic comorbidities" — clipping at the first
        # comma would leave a dangling modifier that misrepresents the criterion.
        return None
    temporal = _temporal_from(sentence)
    for cue in _DRUG_CUES:
        m = re.search(rf"\b{re.escape(cue)}\s+(.+)$", sentence, re.IGNORECASE)
        if m:
            phrase = _clean_phrase(m.group(1))
            if phrase:
                is_procedure = phrase.endswith(_PROCEDURE_SUFFIXES)
                etype = EntityType.PROCEDURE if is_procedure else EntityType.DRUG
                label = "procedure" if is_procedure else "drug"
                return Atom(entity=Entity(text=phrase, type=etype),
                            temporal=temporal), f"{label}:{cue.replace(' ', '_')}"
    for cue in _CONDITION_CUES:
        m = re.search(rf"\b{re.escape(cue)}\s+(.+)$", sentence, re.IGNORECASE)
        if m:
            phrase = _clean_phrase(m.group(1))
            if phrase:
                return Atom(entity=Entity(text=phrase, type=EntityType.CONDITION),
                            temporal=temporal), f"condition:{cue.replace(' ', '_')}"
    return None


def _sentence_to_atom(sentence: str) -> tuple[Atom, str] | None:
    for extractor in (_age_atom, _measurement_atom, _cued_concept_atom):
        try:
            hit = extractor(sentence)
        except ValueError:
            # A schema validator rejected the constraint (e.g. an impossible range).
            # Skipping is correct: the alternative is inventing a plausible bound.
            hit = None
        if hit:
            return hit
    return None


def iter_criterion_sentences(text: str) -> Iterator[tuple[str, str]]:
    """Yield ``(section, sentence)`` for each bullet in an eligibility blob.

    Sentences are the source lines with bullet markers, markdown backslash escapes, and
    redundant whitespace removed. No words are added, removed, or reordered, so the
    stored sentence still reads as the trial wrote it.
    """
    section = "inclusion"
    for raw in text.splitlines():
        line = _ESCAPE_RE.sub(r"\1", raw).strip()
        if not line:
            continue
        header = _HEADER_RE.match(line)
        if header:
            section = header.group(1).lower()
            continue
        # Some records inline the header on the same line as the first bullet.
        low = line.lower()
        if low.startswith("inclusion criteria"):
            section, line = "inclusion", line.split(":", 1)[-1].strip()
        elif low.startswith("exclusion criteria"):
            section, line = "exclusion", line.split(":", 1)[-1].strip()
        line = _BULLET_RE.sub("", line)
        line = _normalize_ws(line)
        if line:
            yield section, line


def extract_atoms(study: dict, fetched_utc: str,
                  stats: ExtractionStats | None = None) -> list[AtomRecord]:
    """Extract atoms from one cached study record."""
    stats = stats if stats is not None else ExtractionStats()
    nct = nct_id(study)
    text = eligibility_text(study)
    if not nct or not text:
        return []
    stats.studies += 1
    posted = first_posted(study)
    records: list[AtomRecord] = []
    for section, sentence in iter_criterion_sentences(text):
        stats.sentences += 1
        if not (MIN_SENTENCE_CHARS <= len(sentence) <= MAX_SENTENCE_CHARS):
            stats.skip("length_out_of_range")
            continue
        low = sentence.lower()
        if any(sp in low for sp in _STOP_PHRASES):
            stats.skip("boilerplate_phrase")
            continue
        hit = _sentence_to_atom(sentence)
        if hit is None:
            stats.skip("no_pattern_matched")
            continue
        atom, pattern = hit
        stats.matched += 1
        stats.hit(pattern)
        records.append(AtomRecord(atom=atom, nct_id=nct, sentence=sentence, section=section,
                                  first_posted=posted, fetched_utc=fetched_utc, pattern=pattern))
    return records


def build_atom_records(studies: list[dict], fetched_utc: str,
                       max_per_study: int | None = None) -> tuple[list[AtomRecord], ExtractionStats]:
    """Extract and de-duplicate atoms across studies.

    Deduplication keys on the serialized atom, so two trials phrasing the same predicate
    identically contribute one atom, attributed to the first NCT ID in sorted order.
    """
    stats = ExtractionStats()
    seen: set[str] = set()
    out: list[AtomRecord] = []
    for study in sorted(studies, key=lambda s: nct_id(s) or ""):
        kept = 0
        for rec in extract_atoms(study, fetched_utc, stats):
            key = rec.atom.model_dump_json()
            if key in seen:
                continue
            seen.add(key)
            out.append(rec)
            kept += 1
            if max_per_study is not None and kept >= max_per_study:
                break
    return out, stats
