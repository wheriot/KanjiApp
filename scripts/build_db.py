"""Build the shipped reference database ``kanji_app/resources/kanji.db``.

Runs the KANJIDIC2, KanjiVG and JMdict importers against a charset file. JLPT
levels are applied from whichever ``kanji_app/resources/jlpt/n{1..5}.txt`` files
exist; each vocab entry inherits the (hardest) level of its kanji. Sources are
downloaded and cached under ``kanji_app/resources/_cache/`` on first run.

Usage:
    uv run python -m scripts.build_db                       # all Jouyou, downloads sources
    uv run python -m scripts.build_db --charset kanji_app/resources/jlpt/n5.txt
    uv run python -m scripts.build_db --kanjidic path/to/kanjidic2.xml \\
        --kanjivg path/to/kanjivg-main.zip --jmdict path/to/JMdict_e.gz
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from kanji_app.data import db
from scripts._common import CHARSET_DIR, DEFAULT_DB, load_charset
from scripts.import_jmdict import _resolve_source as resolve_jmdict
from scripts.import_jmdict import import_jmdict
from scripts.import_kanjidic import _resolve_source as resolve_kanjidic
from scripts.import_kanjidic import import_kanjidic
from scripts.import_kanjivg import _resolve_source as resolve_kanjivg
from scripts.import_kanjivg import import_kanjivg


def _reset_db(path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        target = path.with_name(path.name + suffix)
        target.unlink(missing_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)


def _apply_jlpt_levels(conn: sqlite3.Connection) -> None:
    """Tag kanji from jlpt/n{1..5}.txt (easier level wins on overlap), then vocab."""
    with db.transaction(conn):
        for level in (1, 2, 3, 4, 5):
            path = CHARSET_DIR / f"n{level}.txt"
            if path.exists():
                conn.executemany(
                    "UPDATE kanji SET jlpt = ? WHERE literal = ?",
                    [(level, ch) for ch in load_charset(path)],
                )
        conn.execute(
            """
            UPDATE vocab SET jlpt = (
                SELECT MIN(k.jlpt) FROM vocab_kanji vk
                JOIN kanji k ON k.id = vk.kanji_id
                WHERE vk.vocab_id = vocab.id AND k.jlpt IS NOT NULL
            )
            """
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--charset", type=Path, default=CHARSET_DIR / "joyo.txt")
    parser.add_argument("--kanjidic", help="path or URL to kanjidic2.xml(.gz)")
    parser.add_argument("--kanjivg", help="path or URL to a KanjiVG zip / directory")
    parser.add_argument("--jmdict", help="path or URL to JMdict_e(.gz)")
    parser.add_argument("--no-vocab", action="store_true", help="skip the JMdict vocab import")
    parser.add_argument("--out", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    charset_list = load_charset(args.charset)
    charset = set(charset_list)
    print(f"charset: {args.charset.name} ({len(charset_list)} kanji)")

    print("resolving sources...")
    kanjidic_path = resolve_kanjidic(args.kanjidic)
    kanjivg_path = resolve_kanjivg(args.kanjivg)
    jmdict_path = None if args.no_vocab else resolve_jmdict(args.jmdict)

    _reset_db(args.out)
    conn = db.connect(args.out)
    db.migrate(conn)

    print("importing KANJIDIC2...")
    n_kanji = import_kanjidic(kanjidic_path, conn, charset)

    print("importing KanjiVG...")
    n_svg, missing = import_kanjivg(kanjivg_path, conn, charset)

    n_vocab = 0
    if jmdict_path is not None:
        print("importing JMdict vocab...")
        n_vocab = import_jmdict(jmdict_path, conn, charset)

    print("applying JLPT levels...")
    _apply_jlpt_levels(conn)

    # Ship a compact, single-file database (no WAL sidecars).
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("VACUUM")

    found = {row["literal"] for row in conn.execute("SELECT literal FROM kanji")}
    conn.close()

    absent = [ch for ch in charset_list if ch not in found]
    size_kb = args.out.stat().st_size / 1024
    print(
        f"\nbuilt {args.out} ({size_kb:.0f} KB)\n"
        f"  kanji:           {n_kanji}\n"
        f"  stroke diagrams: {n_svg}\n"
        f"  vocab:           {n_vocab}"
    )
    if missing:
        print(f"  no KanjiVG for:  {' '.join(missing)}")
    if absent:
        print(f"  NOT in KANJIDIC2: {' '.join(absent)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
