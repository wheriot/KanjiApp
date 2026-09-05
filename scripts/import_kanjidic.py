"""Import KANJIDIC2 into the ``kanji`` / ``reading`` / ``meaning`` tables.

KANJIDIC2 is distributed by the EDRDG under CC BY-SA 4.0; attribution is
required (the app ships a Credits screen).

Usage:
    uv run python -m scripts.import_kanjidic [--source PATH_OR_URL] [--db PATH]
                                             [--charset PATH]

With no ``--source`` the file is downloaded (and cached) from edrdg.org. With a
``--charset`` only those kanji are imported; otherwise every entry is.
"""

from __future__ import annotations

import argparse
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from kanji_app.data import db
from scripts._common import CHARSET_DIR, DEFAULT_DB, fetch, load_charset

KANJIDIC_URL = "http://www.edrdg.org/kanjidic/kanjidic2.xml.gz"


def import_kanjidic(
    xml_path: Path,
    conn: sqlite3.Connection,
    charset: set[str] | None = None,
) -> int:
    """Parse ``xml_path`` and upsert entries. Returns the number imported."""
    imported = 0
    with db.transaction(conn):
        for _event, el in ET.iterparse(str(xml_path)):
            if el.tag != "character":
                continue
            literal = el.findtext("literal") or ""
            if literal and (charset is None or literal in charset):
                _upsert_character(conn, el)
                imported += 1
            el.clear()
    return imported


def _upsert_character(conn: sqlite3.Connection, el: ET.Element) -> None:
    literal = el.findtext("literal") or ""
    misc = el.find("misc")
    stroke_count = _first_int(misc, "stroke_count") or 0
    grade = _first_int(misc, "grade")
    jlpt_old = _first_int(misc, "jlpt")
    freq = _first_int(misc, "freq")
    radical = None
    rad_el = el.find("radical/rad_value[@rad_type='classical']")
    if rad_el is not None:
        radical = rad_el.text

    conn.execute(
        """
        INSERT INTO kanji (literal, stroke_count, grade, jlpt_old, frequency, radical)
        VALUES (:literal, :strokes, :grade, :jlpt_old, :freq, :radical)
        ON CONFLICT(literal) DO UPDATE SET
            stroke_count = excluded.stroke_count,
            grade        = excluded.grade,
            jlpt_old     = excluded.jlpt_old,
            frequency    = excluded.frequency,
            radical      = excluded.radical
        """,
        {
            "literal": literal,
            "strokes": stroke_count,
            "grade": grade,
            "jlpt_old": jlpt_old,
            "freq": freq,
            "radical": radical,
        },
    )
    kanji_id = conn.execute("SELECT id FROM kanji WHERE literal = ?", (literal,)).fetchone()[0]
    conn.execute("DELETE FROM reading WHERE kanji_id = ?", (kanji_id,))
    conn.execute("DELETE FROM meaning WHERE kanji_id = ?", (kanji_id,))

    rm = el.find("reading_meaning/rmgroup")
    if rm is None:
        return
    for reading in rm.findall("reading"):
        mapped = {"ja_on": "on", "ja_kun": "kun"}.get(reading.get("r_type", ""))
        if mapped and reading.text:
            conn.execute(
                "INSERT INTO reading (kanji_id, type, value) VALUES (?, ?, ?)",
                (kanji_id, mapped, reading.text),
            )
    for nanori in el.findall("reading_meaning/nanori"):
        if nanori.text:
            conn.execute(
                "INSERT INTO reading (kanji_id, type, value) VALUES (?, 'nanori', ?)",
                (kanji_id, nanori.text),
            )
    for meaning in rm.findall("meaning"):
        # No m_lang attribute means English.
        if meaning.get("m_lang") is None and meaning.text:
            conn.execute(
                "INSERT INTO meaning (kanji_id, value, lang) VALUES (?, ?, 'en')",
                (kanji_id, meaning.text),
            )


def _first_int(parent: ET.Element | None, tag: str) -> int | None:
    if parent is None:
        return None
    text = parent.findtext(tag)
    return int(text) if text and text.isdigit() else None


def _resolve_source(source: str | None) -> Path:
    if source is None:
        return fetch(KANJIDIC_URL, DEFAULT_DB.parent / "_cache" / "kanjidic2.xml")
    if source.startswith(("http://", "https://")):
        return fetch(source, DEFAULT_DB.parent / "_cache" / "kanjidic2.xml")
    return Path(source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="path or URL to kanjidic2.xml(.gz)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--charset",
        type=Path,
        default=CHARSET_DIR / "n5.txt",
        help="charset file to limit the import (pass 'all' for everything)",
    )
    args = parser.parse_args()

    xml_path = _resolve_source(args.source)
    charset: set[str] | None = None
    if str(args.charset).lower() != "all":
        charset = set(load_charset(args.charset))

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(args.db)
    db.migrate(conn)
    count = import_kanjidic(xml_path, conn, charset)
    conn.close()
    print(f"imported {count} kanji into {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
