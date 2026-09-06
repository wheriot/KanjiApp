"""Import example sentences from the Tanaka Corpus (``examples.utf``).

The Tanaka Corpus is distributed by the EDRDG under CC BY-SA 4.0; attribution is
required (the app ships a Credits screen). Each entry is a Japanese/English pair
plus a word-index line listing the dictionary headwords it contains, which lets
us link sentences to vocab without our own tokeniser.

Only short, fully-translated sentences whose kanji are all in the charset are
kept, and at most a few (shortest first) per vocab entry.

Usage:
    uv run python -m scripts.import_tatoeba [--source PATH_OR_URL] [--db PATH]
                                            [--charset PATH]
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from kanji_app.data import db
from scripts._common import CHARSET_DIR, DEFAULT_DB, fetch, load_charset

TANAKA_URL = "http://ftp.edrdg.org/pub/Nihongo/examples.utf.gz"
_MAX_LEN = 45  # Japanese characters
_MIN_LEN = 4
_PER_VOCAB = 4
_HEADWORD = re.compile(r"^([^\s(\[{|~]+)")


def _is_kanji(char: str) -> bool:
    return "一" <= char <= "鿿"


def import_tatoeba(path: Path, conn: sqlite3.Connection, charset: set[str]) -> tuple[int, int]:
    """Returns (sentences kept, vocab links created)."""
    vocab_ids = {
        row["expression"]: row["id"] for row in conn.execute("SELECT id, expression FROM vocab")
    }
    # vocab_id -> list of (length, sentence_id), trimmed to the shortest _PER_VOCAB
    links: dict[int, list[tuple[int, int]]] = {}
    kept: dict[int, tuple[str, str, int]] = {}

    for japanese, english, headwords in _iter_pairs(path):
        if not (_MIN_LEN <= len(japanese) <= _MAX_LEN):
            continue
        if any(_is_kanji(c) and c not in charset for c in japanese):
            continue
        matched = [vocab_ids[h] for h in headwords if h in vocab_ids]
        if not matched:
            continue
        sentence_id = len(kept) + 1
        kept[sentence_id] = (japanese, english, len(japanese))
        for vid in matched:
            bucket = links.setdefault(vid, [])
            bucket.append((len(japanese), sentence_id))

    used: set[int] = set()
    trimmed: list[tuple[int, int]] = []
    for vid, bucket in links.items():
        for _length, sid in sorted(bucket)[:_PER_VOCAB]:
            trimmed.append((vid, sid))
            used.add(sid)

    with db.transaction(conn):
        conn.execute("DELETE FROM sentence")
        conn.executemany(
            "INSERT INTO sentence (id, japanese, english, length) VALUES (?, ?, ?, ?)",
            [(sid, *kept[sid]) for sid in sorted(used)],
        )
        conn.executemany(
            "INSERT INTO vocab_sentence (vocab_id, sentence_id) VALUES (?, ?)", trimmed
        )
    return len(used), len(trimmed)


def _iter_pairs(path: Path) -> Iterator[tuple[str, str, set[str]]]:
    with path.open(encoding="utf-8") as handle:
        a_line: str | None = None
        for raw in handle:
            if raw.startswith("A: "):
                a_line = raw[3:].rstrip("\n")
            elif raw.startswith("B: ") and a_line is not None:
                jp, _, tail = a_line.partition("\t")
                english = tail.split("#ID=")[0].strip()
                if jp and english:
                    yield jp.strip(), english, _headwords(raw[3:])
                a_line = None


def _headwords(b_line: str) -> set[str]:
    out: set[str] = set()
    for token in b_line.split():
        match = _HEADWORD.match(token)
        if match:
            out.add(match.group(1))
    return out


def _resolve_source(source: str | None) -> Path:
    cache = DEFAULT_DB.parent / "_cache" / "examples.utf"
    if source and not source.startswith(("http://", "https://")):
        return Path(source)
    return fetch(source or TANAKA_URL, cache)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="path or URL to examples.utf(.gz)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--charset", type=Path, default=CHARSET_DIR / "joyo.txt")
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f"error: {args.db} does not exist — run build_db first")

    charset = set(load_charset(args.charset))
    conn = db.connect(args.db)
    db.migrate(conn)
    sentences, link_count = import_tatoeba(_resolve_source(args.source), conn, charset)
    conn.close()
    print(f"kept {sentences} sentences, {link_count} vocab links, in {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
