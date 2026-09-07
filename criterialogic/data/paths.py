"""Where the committed data lives, resolved rather than assumed.

The snapshot and the atom pool are committed to the repository, and every default path to
them used to be written relative to the process working directory
(``Path("data/ctgov_atom_pool.json")``). That works when you run from a clone and breaks
everywhere else: ``pip install -e .`` puts a ``criterialogic-eval`` command on the PATH,
and running it from your home directory raised ``AtomPoolUnavailable`` telling you to
rebuild a pool that was sitting on disk the whole time.

Resolution order, first hit wins:

1. ``$CRITERIALOGIC_DATA_DIR`` — an explicit override, for a checked-out snapshot kept
   outside the repository or a CI cache directory.
2. ``./data`` relative to the working directory — the clone case, unchanged.
3. ``<repo root>/data``, found by walking up from this file — the installed-from-a-clone
   case, which is what ``pip install -e .`` produces.

If none exists the caller still gets the pool's own build instructions; this module only
decides *where to look*, and never invents a location.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "CRITERIALOGIC_DATA_DIR"

#: Files that identify a directory as the benchmark's data directory rather than some
#: other directory that happens to be called "data".
_MARKERS = ("ctgov_cache", "ctgov_atom_pool.json")


def _looks_like_data_dir(path: Path) -> bool:
    return path.is_dir() and any((path / m).exists() for m in _MARKERS)


def candidate_data_dirs() -> list[Path]:
    """Every location that will be tried, in order. Useful in error messages."""
    out: list[Path] = []
    override = os.environ.get(ENV_VAR)
    if override:
        out.append(Path(override).expanduser())
    out.append(Path.cwd() / "data")
    # criterialogic/data/paths.py -> criterialogic/data -> criterialogic -> <repo root>
    out.append(Path(__file__).resolve().parents[2] / "data")
    seen: set[Path] = set()
    unique = []
    for p in out:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def data_dir() -> Path:
    """The benchmark data directory.

    Returns the first candidate that looks like the real thing, else the working-directory
    candidate — so a fresh checkout that has not been built yet still produces a sensible
    path in the error message a caller raises.
    """
    candidates = candidate_data_dirs()
    for path in candidates:
        if _looks_like_data_dir(path):
            return path
    override = os.environ.get(ENV_VAR)
    if override:
        # An explicit override that does not resolve is a mistake worth naming, rather
        # than something to silently fall back from.
        raise FileNotFoundError(
            f"{ENV_VAR}={override!r} does not contain {' or '.join(_MARKERS)}. "
            f"Point it at the directory holding the committed snapshot, or unset it."
        )
    return candidates[1]  # ./data, so the message a caller prints names a real path


def default_cache_dir() -> Path:
    return data_dir() / "ctgov_cache"


def default_pool_path() -> Path:
    return data_dir() / "ctgov_atom_pool.json"


def describe_resolution() -> dict:
    """What was searched and what was found. Printed by the build scripts."""
    candidates = candidate_data_dirs()
    return {
        "env_var": ENV_VAR,
        "env_value": os.environ.get(ENV_VAR),
        "candidates": [str(p) for p in candidates],
        "resolved": str(next((p for p in candidates if _looks_like_data_dir(p)), None)),
    }
