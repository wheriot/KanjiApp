"""Shared helpers for the data-import scripts (not part of the shipped package)."""

from __future__ import annotations

import gzip
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOURCES = REPO_ROOT / "kanji_app" / "resources"
DEFAULT_DB = RESOURCES / "kanji.db"
CHARSET_DIR = RESOURCES / "jlpt"


def load_charset(path: Path) -> list[str]:
    """Read a one-kanji-per-line charset file, ignoring ``#`` comments/blanks.

    Order is preserved so a deck built from the file follows the file's order.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        char = line[0]
        if char not in seen:
            seen.add(char)
            out.append(char)
    return out


def fetch(url: str, dest: Path) -> Path:
    """Download ``url`` to ``dest`` unless it already exists. Gunzips ``.gz``."""
    if dest.exists():
        print(f"  using cached {dest.name}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    if url.endswith(".gz") and not dest.name.endswith(".gz"):
        data = gzip.decompress(data)
    dest.write_bytes(data)
    return dest


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)
