"""The atom pool that Task D composes over, and its provenance.

Task D builds nested AND/OR/NOT expressions out of *atoms*. Where those atoms come
from is a claim the benchmark makes about itself, so it is explicit here rather than
implicit in the generator:

``ctgov``
    Predicates extracted from verbatim ClinicalTrials.gov eligibility text by
    :mod:`criterialogic.data.loaders.ctgov`. Each atom carries its source NCT ID and
    source sentence, so any generated item resolves back to real trial prose. Built by
    ``scripts/fetch_ctgov_atoms.py`` into ``data/ctgov_atom_pool.json``.

``n2c2_derived``
    The leaf predicates of the 13 public n2c2 criterion definitions. This is what the
    generator used historically. It is still available, but it must be requested
    explicitly and it labels its output ``Source.N2C2_DERIVED``, because those criteria
    long predate every evaluated model and support no contamination argument.

Only the *atoms* are real in either case. The nesting that combines them is synthetic
by construction, and nothing here should be read as a claim that real trials state
criteria at these nesting depths.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from criterialogic.schema.logical_form import SCHEMA_VERSION, Atom, Source

DEFAULT_POOL_PATH = Path("data/ctgov_atom_pool.json")
POOL_FORMAT_VERSION = "1"

CTGOV = "ctgov"
N2C2_DERIVED = "n2c2_derived"
ATOM_SOURCES = (CTGOV, N2C2_DERIVED)

_SOURCE_ENUM = {CTGOV: Source.CTGOV, N2C2_DERIVED: Source.N2C2_DERIVED}


class AtomPoolUnavailable(FileNotFoundError):
    """The ClinicalTrials.gov atom pool has not been built.

    Deliberately fatal. Falling back to the n2c2 leaves here is what previously let the
    manuscript describe a data source the code never touched.
    """


@dataclass(frozen=True)
class PooledAtom:
    """An atom together with the trial text it was extracted from."""

    atom: Atom
    nct_id: str | None
    sentence: str | None
    section: str | None
    first_posted: str | None
    fetched_utc: str | None
    pattern: str | None


@dataclass(frozen=True)
class AtomPool:
    """A loaded pool: the atoms, their provenance, and a digest of the source file."""

    source: str
    entries: tuple[PooledAtom, ...]
    sha256: str
    metadata: dict

    def __post_init__(self) -> None:
        index = {e.atom.model_dump_json(): e for e in self.entries}
        object.__setattr__(self, "_index", index)

    @property
    def atoms(self) -> list[Atom]:
        return [e.atom for e in self.entries]

    @property
    def logical_form_source(self) -> Source:
        return _SOURCE_ENUM[self.source]

    def provenance_for(self, atom: Atom) -> PooledAtom | None:
        """Resolve an atom back to the trial and sentence it came from."""
        return self._index.get(atom.model_dump_json())  # type: ignore[attr-defined]

    def nct_ids_for(self, atoms: list[Atom]) -> list[str]:
        """Distinct source NCT IDs behind a set of atoms, in first-seen order."""
        out: list[str] = []
        for a in atoms:
            p = self.provenance_for(a)
            if p and p.nct_id and p.nct_id not in out:
                out.append(p.nct_id)
        return out

    def __len__(self) -> int:
        return len(self.entries)


def digest(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_pool(records, stats, query_manifest: dict, path: Path | str = DEFAULT_POOL_PATH) -> Path:
    """Serialize extracted atom records. Key order is fixed so reruns are byte-stable."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pool_format_version": POOL_FORMAT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "atom_source": CTGOV,
        "query": query_manifest,
        "extraction": stats.to_json(),
        "n_atoms": len(records),
        "atoms": [r.to_json() for r in records],
    }
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
                 encoding="utf-8")
    return p


def load_ctgov_pool(path: Path | str = DEFAULT_POOL_PATH) -> AtomPool:
    """Load the ClinicalTrials.gov pool, or fail with instructions for building it."""
    p = Path(path)
    if not p.is_file():
        raise AtomPoolUnavailable(
            f"ClinicalTrials.gov atom pool not found at '{p}'.\n"
            f"Build it with:\n"
            f"    python scripts/fetch_ctgov_atoms.py --limit 200\n"
            f"That fetches Phase-IV interventional studies from the public v2 API into "
            f"data/ctgov_cache/ and writes the pool file. It needs network access once; "
            f"afterwards the cache serves every run.\n"
            f"To compose over the public n2c2 criterion leaves instead, pass "
            f"atom_source='{N2C2_DERIVED}' explicitly — that pool supports no "
            f"contamination claim and is labelled Source.N2C2_DERIVED."
        )
    raw = json.loads(p.read_text(encoding="utf-8"))
    entries = tuple(
        PooledAtom(
            atom=Atom.model_validate(e["atom"]),
            nct_id=e.get("nct_id"),
            sentence=e.get("sentence"),
            section=e.get("section"),
            first_posted=e.get("first_posted"),
            fetched_utc=e.get("fetched_utc"),
            pattern=e.get("pattern"),
        )
        for e in raw.get("atoms", [])
    )
    if not entries:
        raise AtomPoolUnavailable(
            f"Atom pool '{p}' contains no atoms. Re-run scripts/fetch_ctgov_atoms.py; "
            f"an empty pool cannot generate Task D items."
        )
    meta = {k: v for k, v in raw.items() if k != "atoms"}
    return AtomPool(source=CTGOV, entries=entries, sha256=digest(p), metadata=meta)


def load_n2c2_derived_pool() -> AtomPool:
    """The historical pool: leaf predicates of the 13 public n2c2 criteria."""
    from criterialogic.data.n2c2_criteria import n2c2_criteria_as_logical_forms
    from criterialogic.data.synthetic import _collect_atoms

    entries: list[PooledAtom] = []
    seen: set[str] = set()
    for form in n2c2_criteria_as_logical_forms():
        tag = form.metadata.get("tag", form.criterion_id)
        for atom in _collect_atoms(form.expression):
            key = atom.model_dump_json()
            if key in seen:
                continue
            seen.add(key)
            entries.append(PooledAtom(atom=atom, nct_id=None, sentence=form.text,
                                      section=form.polarity.value, first_posted=None,
                                      fetched_utc=None, pattern=f"n2c2:{tag}"))
    blob = json.dumps([e.atom.model_dump(mode="json") for e in entries], sort_keys=True)
    return AtomPool(
        source=N2C2_DERIVED,
        entries=tuple(entries),
        sha256=hashlib.sha256(blob.encode("utf-8")).hexdigest(),
        metadata={"atom_source": N2C2_DERIVED, "n_atoms": len(entries),
                  "note": "Leaf predicates of the 13 public n2c2 criterion definitions."},
    )


def load_pool(atom_source: str = CTGOV, path: Path | str = DEFAULT_POOL_PATH) -> AtomPool:
    if atom_source == CTGOV:
        return load_ctgov_pool(path)
    if atom_source == N2C2_DERIVED:
        return load_n2c2_derived_pool()
    raise ValueError(f"Unknown atom_source '{atom_source}'; expected one of {ATOM_SOURCES}.")
