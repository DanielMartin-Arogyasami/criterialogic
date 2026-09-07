"""Load a local ``.env`` into ``os.environ`` without adding a dependency.

Existing process variables win, so a shell export still overrides the file.
The file itself is gitignored; only ``.env.example`` is committed.
"""
from __future__ import annotations

import os
from pathlib import Path

_LOADED: Path | None = None


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path.cwd()


def load_dotenv(path: Path | str | None = None) -> Path | None:
    """Read KEY=VALUE lines into the environment. Returns the path loaded, or None."""
    global _LOADED
    candidate = Path(path) if path else repo_root() / ".env"
    if not candidate.is_file():
        return None
    for raw in candidate.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
    _LOADED = candidate
    return candidate


load_dotenv()
