"""Import KanjiVG stroke-order SVGs into the ``kanjivg`` table.

KanjiVG is by Ulrich Apel / the KanjiVG project, licensed CC BY-SA 3.0;
attribution is required (the app ships a Credits screen).

Usage:
    uv run python -m scripts.import_kanjivg [--source PATH_OR_URL] [--db PATH]
                                            [--charset PATH]

``--source`` may be a ``.zip`` release asset, an extracted directory, or a URL.
With no ``--source`` the latest release zip is downloaded and cached. Only SVGs
for kanji already present in the ``kanji`` table are imported.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

from kanji_app.data import db
from scripts._common import CHARSET_DIR, DEFAULT_DB, fetch, load_charset

RELEASES_API = "https://api.github.com/repos/KanjiVG/kanjivg/releases/latest"
BASENAME_RE = re.compile(r"^0*([0-9a-f]+)\.svg$")
PATH_RE = re.compile(r"<path[\s>]")


def _codepoint_name(literal: str) -> str:
    return f"{ord(literal):05x}"


def _svgs_from_zip(zip_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name
            match = BASENAME_RE.match(name)
            if match:
                out[match.group(1).zfill(5)] = zf.read(info).decode("utf-8")
    return out


def _svgs_from_dir(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for svg in root.rglob("*.svg"):
        match = BASENAME_RE.match(svg.name)
        if match:
            out[match.group(1).zfill(5)] = svg.read_text(encoding="utf-8")
    return out


def load_svgs(source: Path) -> dict[str, str]:
    if source.is_dir():
        return _svgs_from_dir(source)
    if source.suffix == ".zip":
        return _svgs_from_zip(source)
    raise SystemExit(f"error: don't know how to read {source}")


def import_kanjivg(
    source: Path,
    conn: sqlite3.Connection,
    charset: set[str] | None = None,
) -> tuple[int, list[str]]:
    """Store SVGs for kanji in the DB. Returns (imported, missing literals)."""
    svgs = load_svgs(source)
    rows = conn.execute("SELECT id, literal FROM kanji").fetchall()

    imported = 0
    missing: list[str] = []
    with db.transaction(conn):
        for row in rows:
            literal = row["literal"]
            if charset is not None and literal not in charset:
                continue
            svg = svgs.get(_codepoint_name(literal))
            if svg is None:
                missing.append(literal)
                continue
            conn.execute(
                """
                INSERT INTO kanjivg (kanji_id, stroke_count, svg)
                VALUES (:id, :strokes, :svg)
                ON CONFLICT(kanji_id) DO UPDATE SET
                    stroke_count = excluded.stroke_count,
                    svg          = excluded.svg
                """,
                {
                    "id": row["id"],
                    "strokes": len(PATH_RE.findall(svg)),
                    "svg": svg,
                },
            )
            imported += 1
    return imported, missing


def _latest_release_zip() -> str:
    req = urllib.request.Request(RELEASES_API, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as resp:
        release = json.load(resp)
    for asset in release.get("assets", []):
        if asset["name"].endswith("-main.zip"):
            return str(asset["browser_download_url"])
    raise SystemExit("error: no '-main.zip' asset in the latest KanjiVG release")


def _resolve_source(source: str | None) -> Path:
    cache = DEFAULT_DB.parent / "_cache"
    if source is None:
        return fetch(_latest_release_zip(), cache / "kanjivg-main.zip")
    if source.startswith(("http://", "https://")):
        return fetch(source, cache / "kanjivg-main.zip")
    return Path(source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="path or URL to a KanjiVG zip / directory")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--charset", type=Path, default=CHARSET_DIR / "n5.txt")
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(
            f"error: {args.db} does not exist — run 'python -m scripts.import_kanjidic' first"
        )

    charset: set[str] | None = None
    if str(args.charset).lower() != "all":
        charset = set(load_charset(args.charset))

    source = _resolve_source(args.source)
    conn = db.connect(args.db)
    db.migrate(conn)
    imported, missing = import_kanjivg(source, conn, charset)
    conn.close()
    print(f"imported {imported} stroke diagrams into {args.db}")
    if missing:
        print(f"no KanjiVG SVG for {len(missing)}: {' '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
