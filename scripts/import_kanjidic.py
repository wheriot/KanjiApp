"""Importer for KANJIDIC2 -> the app's SQLite ``kanji``/``reading``/``meaning`` tables.

STUB (Phase 1). KANJIDIC2 is distributed by the EDRDG under CC BY-SA 4.0 and
attribution is required; the app ships a Credits screen for this.

Planned usage:
    uv run python scripts/import_kanjidic.py path/to/kanjidic2.xml kanji_app/resources/kanji.db
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    print(__doc__)
    print("Not implemented yet — see PLAN.md Phase 1.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
