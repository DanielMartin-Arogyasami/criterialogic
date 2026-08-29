"""Data acquisition for CriteriaLogic — fetch the releasable sources, point to the gated one.
Release boundary, enforced in code:
  * **Chia** (CC-BY 4.0)            → downloaded from figshare as raw brat .txt/.ann.
  * **ClinicalTrials.gov** (public) → cached from the public API v2 (no download needed at run time).
  * **n2c2 2018** (DUA-gated)       → **never downloaded**; we only report local status and the portal URL.
Dependency posture: standard library only (``urllib``), so ``pip install criterialogic`` is
sufficient. An optional Hugging Face route (``download_chia_hf``) additionally needs ``datasets``.
The functions here are importable and unit-testable; ``scripts/download_data.py`` is a thin CLI
over them (mirroring how ``criterialogic.cli`` backs ``scripts/run_eval.py``).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# ---- Source coordinates (verifiable, public) ------------------------------- #
FIGSHARE_API = "https://api.figshare.com/v2/articles"
CHIA_FIGSHARE_ARTICLE = 11855817  # "Chia Annotated Datasets" (DOI 10.6084/m9.figshare.11855817)
CHIA_HF_DATASET = "bigbio/chia"
N2C2_PORTAL = "https://n2c2.dbmi.hms.harvard.edu/"
DEFAULT_DATA_ROOT = Path("data/raw")
_USER_AGENT = "CriteriaLogic-downloader/0.1 (+https://github.com/USERNAME/criterialogic)"
class DownloadError(RuntimeError):
    """Raised when a releasable source cannot be retrieved."""
# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #
def _http_json(url: str, timeout: int = 60) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.URLError as e:  # pragma: no cover - network dependent
        raise DownloadError(
            f"Could not reach {url} ({e}). If you are behind a restricted network, run this in your "
            f"own environment or ask an administrator to allow the domain."
        ) from e
def _download_file(url: str, dest: Path, expected_md5: str | None = None, timeout: int = 300) -> Path:
    """Stream a URL to ``dest`` (atomic), optionally verifying an MD5 checksum."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    md5 = hashlib.md5()
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as fh:
            for chunk in iter(lambda: resp.read(1 << 20), b""):
                fh.write(chunk)
                md5.update(chunk)
    except urllib.error.URLError as e:  # pragma: no cover - network dependent
        raise DownloadError(f"Failed to download {url} ({e}).") from e
    if expected_md5 and md5.hexdigest() != expected_md5:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"Checksum mismatch for {url}: got {md5.hexdigest()}, expected {expected_md5}.")
    tmp.replace(dest)
    return dest
def _extract_archives(archives: list[Path], dest: Path) -> int:
    """Extract every .zip in ``archives`` into ``dest``. Returns the count of .ann files found after."""
    dest.mkdir(parents=True, exist_ok=True)
    for arc in archives:
        if arc.suffix.lower() == ".zip":
            with zipfile.ZipFile(arc) as zf:
                zf.extractall(dest)
    return sum(1 for _ in dest.rglob("*.ann"))
# --------------------------------------------------------------------------- #
# Chia (releasable)
# --------------------------------------------------------------------------- #
def download_chia_figshare(dest: Path | str = DEFAULT_DATA_ROOT / "chia", force: bool = False) -> dict:
    """Download + extract the Chia brat corpus from figshare into ``dest``.
    Idempotent: if ``dest`` already contains .ann files and ``force`` is False, it is a no-op.
    Returns a small summary dict (files downloaded, .ann count, destination).
    """
    dest = Path(dest)
    existing = sum(1 for _ in dest.rglob("*.ann"))
    if existing and not force:
        return {"status": "already_present", "ann_files": existing, "dest": str(dest)}
    meta = _http_json(f"{FIGSHARE_API}/{CHIA_FIGSHARE_ARTICLE}")
    files = meta.get("files", []) if isinstance(meta, dict) else []
    if not files:
        raise DownloadError(f"figshare article {CHIA_FIGSHARE_ARTICLE} returned no files.")
    with tempfile.TemporaryDirectory() as td:
        downloaded: list[Path] = []
        for f in files:
            url = f.get("download_url")
            name = f.get("name", "chia_file")
            if not url:
                continue
            local = _download_file(url, Path(td) / name, expected_md5=f.get("computed_md5"))
            downloaded.append(local)
        n_ann = _extract_archives(downloaded, dest)
        # also copy any loose (non-zip) .txt/.ann that came straight from figshare
        for f in downloaded:
            if f.suffix.lower() in {".ann", ".txt"}:
                shutil.copy2(f, dest / f.name)
        n_ann = sum(1 for _ in dest.rglob("*.ann"))
    if n_ann == 0:
        raise DownloadError(
            f"Downloaded {len(downloaded)} figshare file(s) but found no .ann files under {dest}. "
            f"Inspect the archive layout; Chia ships brat .txt/.ann pairs."
        )
    return {"status": "downloaded", "files": len(downloaded), "ann_files": n_ann, "dest": str(dest)}
def download_chia_hf(dest: Path | str = DEFAULT_DATA_ROOT / "chia_hf") -> dict:
    """Alternative Chia route via Hugging Face (`bigbio/chia`). Requires the `datasets` package.
    Note: this yields pre-parsed records, NOT raw brat .txt/.ann, so it does not feed
    `loaders.chia.load_chia_dir` directly; use the figshare route for the brat parser.
    """
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as e:
        raise DownloadError(
            "The Hugging Face route needs `datasets` (pip install datasets). "
            "For the brat .txt/.ann the toolkit parses, prefer download_chia_figshare()."
        ) from e
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    ds = load_dataset(CHIA_HF_DATASET, trust_remote_code=True)  # pragma: no cover - heavy/optional
    out = dest / "chia_hf.jsonl"
    with open(out, "w") as fh:
        for split in ds:  # type: ignore
            for row in ds[split]:  # type: ignore
                fh.write(json.dumps(row, default=str) + "\n")
    return {"status": "downloaded_hf", "dest": str(out)}
# --------------------------------------------------------------------------- #
# ClinicalTrials.gov (public) — cache eligibility text for the Task-D atom pool
# --------------------------------------------------------------------------- #
def cache_ctgov_criteria(
    query: str = "type 2 diabetes",
    n: int = 50,
    dest: Path | str = DEFAULT_DATA_ROOT / "ctgov",
    filename: str | None = None,
) -> dict:
    """Fetch eligibility text for ``n`` trials matching ``query`` and cache as JSON."""
    from criterialogic.data.loaders import ctgov
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    nct_ids = [x for x in ctgov.search_trials(query, page_size=n) if x]
    criteria = ctgov.fetch_eligibility(nct_ids)
    safe = filename or ("ctgov_" + "".join(c if c.isalnum() else "_" for c in query)[:40] + ".json")
    out = dest / safe
    out.write_text(json.dumps(criteria, indent=2))
    return {"status": "cached", "query": query, "n_trials": len(criteria), "path": str(out)}
# --------------------------------------------------------------------------- #
# n2c2 (DUA-gated) — status only, never downloaded
# --------------------------------------------------------------------------- #
def n2c2_status(dest: Path | str = DEFAULT_DATA_ROOT / "n2c2_2018") -> dict:
    """Report whether DUA-obtained n2c2 XML files are present locally. Never downloads."""
    dest = Path(dest)
    files = sorted(dest.glob("*.xml")) if dest.exists() else []
    return {
        "present": bool(files),
        "n_files": len(files),
        "dest": str(dest),
        "portal": N2C2_PORTAL,
        "note": "n2c2 is DUA-gated and never downloaded/committed; obtain via the portal and place XML here.",
    }
def verify(data_root: Path | str = DEFAULT_DATA_ROOT) -> dict:
    """Summarize what is present locally across all sources."""
    root = Path(data_root)
    chia_ann = sum(1 for _ in (root / "chia").rglob("*.ann")) if (root / "chia").exists() else 0
    ctgov_files = len(list((root / "ctgov").glob("*.json"))) if (root / "ctgov").exists() else 0
    return {
        "chia_ann_files": chia_ann,
        "ctgov_cached_queries": ctgov_files,
        "n2c2": n2c2_status(root / "n2c2_2018"),
    }
