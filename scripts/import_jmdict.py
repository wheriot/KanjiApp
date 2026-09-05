"""Import a JLPT-appropriate vocabulary subset from JMdict.

JMdict is distributed by the EDRDG under CC BY-SA 4.0; attribution is required
(the app ships a Credits screen).

The subset is deliberately narrow: entries that have a kanji spelling built
*only* from the charset's kanji, carry a "common word" priority marker, and are
not tagged rare/archaic. That keeps the vocab tied to the kanji being studied.

Usage:
    uv run python -m scripts.import_jmdict [--source PATH_OR_URL] [--db PATH]
                                           [--charset PATH]
"""

from __future__ import annotations

import argparse
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from kanji_app.data import db
from scripts._common import CHARSET_DIR, DEFAULT_DB, fetch, load_charset

JMDICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz"
_COMMON_PRIORITIES = {"news1", "ichi1", "spec1"}
_EXCLUDE_MISC = {"rare term", "archaism", "obsolete term", "obscure term"}
_MAX_GLOSSES = 5


def _is_kanji(char: str) -> bool:
    return "一" <= char <= "鿿"


def import_jmdict(
    xml_path: Path,
    conn: sqlite3.Connection,
    charset: set[str],
) -> int:
    kanji_ids = {row["literal"]: row["id"] for row in conn.execute("SELECT id, literal FROM kanji")}
    imported = 0
    with db.transaction(conn):
        conn.execute("DELETE FROM vocab")  # vocab tables are rebuilt wholesale
        for _event, entry in ET.iterparse(str(xml_path)):
            if entry.tag != "entry":
                continue
            parsed = _parse_entry(entry, charset)
            if parsed is not None:
                _insert(conn, parsed, kanji_ids)
                imported += 1
            entry.clear()
    return imported


class _Entry:
    __slots__ = ("expression", "glosses", "kana")

    def __init__(self, expression: str, kana: str, glosses: list[str]) -> None:
        self.expression = expression
        self.kana = kana
        self.glosses = glosses


def _parse_entry(entry: ET.Element, charset: set[str]) -> _Entry | None:
    k_eles = entry.findall("k_ele")
    if not k_eles:
        return None
    keb = k_eles[0].findtext("keb") or ""
    priorities = {p.text for p in k_eles[0].findall("ke_pri")}
    if priorities.isdisjoint(_COMMON_PRIORITIES):
        return None

    kanji_chars = [c for c in keb if _is_kanji(c)]
    if not kanji_chars or any(c not in charset for c in kanji_chars):
        return None

    misc = {m.text for sense in entry.findall("sense") for m in sense.findall("misc")}
    if misc & _EXCLUDE_MISC:
        return None

    glosses = [
        g.text
        for sense in entry.findall("sense")
        for g in sense.findall("gloss")
        if g.get("g_type") is None and g.text
    ][:_MAX_GLOSSES]
    reb = entry.findtext("r_ele/reb") or ""
    if not glosses or not reb:
        return None

    return _Entry(expression=keb, kana=reb, glosses=glosses)


def _insert(conn: sqlite3.Connection, entry: _Entry, kanji_ids: dict[str, int]) -> None:
    cursor = conn.execute(
        "INSERT INTO vocab (expression, kana) VALUES (?, ?)",
        (entry.expression, entry.kana),
    )
    vocab_id = cursor.lastrowid
    conn.executemany(
        "INSERT INTO vocab_gloss (vocab_id, value) VALUES (?, ?)",
        [(vocab_id, g) for g in entry.glosses],
    )
    linked = {kanji_ids[c] for c in entry.expression if _is_kanji(c) and c in kanji_ids}
    conn.executemany(
        "INSERT OR IGNORE INTO vocab_kanji (vocab_id, kanji_id) VALUES (?, ?)",
        [(vocab_id, kid) for kid in linked],
    )


def _resolve_source(source: str | None) -> Path:
    cache = DEFAULT_DB.parent / "_cache" / "JMdict_e"
    if source and not source.startswith(("http://", "https://")):
        return Path(source)
    return fetch(source or JMDICT_URL, cache)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="path or URL to JMdict_e(.gz)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--charset", type=Path, default=CHARSET_DIR / "n5.txt")
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f"error: {args.db} does not exist — run build_db first")

    charset = set(load_charset(args.charset))
    xml_path = _resolve_source(args.source)
    conn = db.connect(args.db)
    db.migrate(conn)
    count = import_jmdict(xml_path, conn, charset)
    conn.close()
    print(f"imported {count} vocab entries into {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
