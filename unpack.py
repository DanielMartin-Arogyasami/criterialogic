#!/usr/bin/env python3
"""Reconstruct the CriteriaLogic repository from the single-file Markdown bundle.
Usage:
    python unpack.py CriteriaLogic_bundle.md [dest_dir]    # dest_dir defaults to "."
Each file in the bundle is a section of the form:
    ### FILE: <relative/path>
    ````<lang>
    ...verbatim file contents...
    ````
The opening fence is four or more backticks (so any ``` blocks *inside* a file are
preserved verbatim); the matching closing fence is a line of exactly those backticks.
"""
from __future__ import annotations

import pathlib
import re
import sys

_HEADER = re.compile(r"^### FILE:\s*(.+?)\s*$")
_FENCE = re.compile(r"^(`{3,})")
def unpack(bundle_path: str, dest_dir: str = ".") -> int:
    lines = pathlib.Path(bundle_path).read_text(encoding="utf-8").splitlines()
    dest = pathlib.Path(dest_dir)
    i, n, written = 0, len(lines), 0
    while i < n:
        m = _HEADER.match(lines[i])
        if not m:
            i += 1
            continue
        relpath = m.group(1).strip()
        i += 1
        while i < n and not _FENCE.match(lines[i]):  # find opening fence
            i += 1
        if i >= n:
            break
        ticks = _FENCE.match(lines[i]).group(1)
        i += 1
        body: list[str] = []
        while i < n and lines[i].strip() != ticks:  # collect until closing fence
            body.append(lines[i])
            i += 1
        i += 1  # consume closing fence
        out = dest / relpath
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(body) + "\n", encoding="utf-8")
        written += 1
        print(f"wrote {out}")
    print(f"done: reconstructed {written} files into {dest.resolve()}")
    return written
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python unpack.py <bundle.md> [dest_dir]")
        sys.exit(1)
    unpack(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
