"""The atom pool the compositional stress test composes over, and its provenance.

Arm 2 builds nested AND/OR/NOT expressions out of *atoms*. Where those atoms come from
is a claim the benchmark makes about itself, so it is explicit here rather than
implicit in the generator. There is exactly one pool:

``ctgov``
    Predicates extracted from verbatim ClinicalTrials.gov eligibility text by
    :mod:`criterialogic.data.loaders.ctgov`, drawn from the dated snapshot described in
    ``data/ctgov_cache/MANIFEST.json``. Each atom carries its source NCT ID, source
    sentence, and the trial's first-posted date, so any generated item resolves back to
    real trial prose and the contamination argument is checkable rather than asserted.
    Built by ``scripts/fetch_ctgov_snapshot.py`` into ``data/ctgov_atom_pool.json``.

v0.1 also shipped an ``n2c2_derived`` pool built from the leaf predicates of the 13
public n2c2 criterion definitions. It is gone: those criteria predate every evaluated
model and so support no contamination argument, and keeping a second pool invited
silent mixing. See docs/V2_SCOPE.md.

Only the *atoms* are real. The nesting that combines them is synthetic by
construction, and nothing here should be read as a claim that real trials state
criteria at these nesting depths.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from criterialogic.data.paths import default_pool_path
from criterialogic.schema.logical_form import SCHEMA_VERSION, Atom, Source

#: Resolved rather than assumed, so the installed console script works from any working
#: directory. See :mod:`criterialogic.data.paths`.
DEFAULT_POOL_PATH = default_pool_path()
POOL_FORMAT_VERSION = "1"

CTGOV = "ctgov"
ATOM_SOURCES = (CTGOV,)

_SOURCE_ENUM = {CTGOV: Source.CTGOV}


class AtomPoolUnavailable(FileNotFoundError):
    """The ClinicalTrials.gov atom pool has not been built.

    Deliberately fatal. Falling back to some other atom source here is what previously
    let the manuscript describe a data source the code never touched.
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
        from criterialogic.data.paths import describe_resolution
        raise AtomPoolUnavailable(
            f"ClinicalTrials.gov atom pool not found at '{p}'.\n"
            f"Searched: {describe_resolution()['candidates']}\n"
            f"Set CRITERIALOGIC_DATA_DIR to point at the committed snapshot, or run from "
            f"a clone.\n"
            f"Build it with:\n"
            f"    python scripts/fetch_ctgov_snapshot.py --limit 300\n"
            f"That fetches studies from the public ClinicalTrials.gov v2 API into "
            f"data/ctgov_cache/ and writes the pool file. It needs network access once; "
            f"afterwards the committed cache serves every run offline."
        )
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise AtomPoolUnavailable(
            f"Atom pool '{p}' is not readable JSON ({e}). Rebuild it with "
            f"scripts/fetch_ctgov_snapshot.py --offline rather than editing it by hand: "
            f"the pool digest is stamped on every generated item."
        ) from e
    if not isinstance(raw, dict):
        raise AtomPoolUnavailable(f"Atom pool '{p}' must be a JSON object.")
    try:
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
    except (KeyError, TypeError, ValueError) as e:
        raise AtomPoolUnavailable(
            f"Atom pool '{p}' has a malformed entry ({type(e).__name__}: {e}). Every entry "
            f"needs an 'atom' matching the current schema; rebuild rather than patch."
        ) from e
    if not entries:
        raise AtomPoolUnavailable(
            f"Atom pool '{p}' contains no atoms. Re-run scripts/fetch_ctgov_snapshot.py; "
            f"an empty pool cannot generate Task D items."
        )
    meta = {k: v for k, v in raw.items() if k != "atoms"}
    return AtomPool(source=CTGOV, entries=entries, sha256=digest(p), metadata=meta)


def load_pool(atom_source: str = CTGOV, path: Path | str = DEFAULT_POOL_PATH) -> AtomPool:
    if atom_source == CTGOV:
        return load_ctgov_pool(path)
    raise ValueError(f"Unknown atom_source '{atom_source}'; expected one of {ATOM_SOURCES}.")
