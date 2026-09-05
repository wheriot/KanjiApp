"""Regenerate the charset files under ``kanji_app/resources/jlpt/``.

- ``joyo.txt``  every Jouyou kanji (KANJIDIC2 grades 1-6 and 8) — the default
  build scope.
- ``n1.txt`` .. ``n5.txt``  approximate modern JLPT levels.

``n5.txt`` is a hand-curated list and is left untouched. The others are derived
from KANJIDIC2's legacy pre-2010 JLPT levels, which map to the modern scale as
follows (cumulative counts line up well, except that the old data predates N3,
so no ``n3.txt`` is produced):

    legacy 4 -> N5      legacy 3 -> N4      legacy 2 -> N2
    legacy 1 (+ any Jouyou kanji with no legacy level) -> N1

Edit the files freely afterwards; ``build_db`` just reads whatever is there.

Usage:
    uv run python -m scripts.make_charsets [--kanjidic PATH_OR_URL]
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET

from scripts._common import CHARSET_DIR
from scripts.import_kanjidic import _resolve_source

_JOUYOU_GRADES = {"1", "2", "3", "4", "5", "6", "8"}
_LEGACY_TO_MODERN = {"4": 5, "3": 4, "2": 2, "1": 1}

_HEADER = {
    "joyo": "# Every Jouyou kanji (KANJIDIC2 grades 1-6, 8). The default build scope.",
    "n1": "# Approximate JLPT N1 — legacy JLPT level 1 plus Jouyou kanji with no legacy level.",
    "n2": "# Approximate JLPT N2 — from KANJIDIC2's legacy pre-2010 JLPT level 2.",
    "n4": "# Approximate JLPT N4 — from KANJIDIC2's legacy pre-2010 JLPT level 3.",
}
_HEADER_COMMON = (
    "# Regenerate with: uv run python -m scripts.make_charsets\n"
    "# One kanji per line; '#' lines are ignored. Edit freely.\n\n"
)


def _write(name: str, kanji: list[str]) -> None:
    path = CHARSET_DIR / f"{name}.txt"
    path.write_text(
        f"{_HEADER[name]}\n{_HEADER_COMMON}" + "\n".join(kanji) + "\n", encoding="utf-8"
    )
    print(f"  {path.name}: {len(kanji)} kanji")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kanjidic", help="path or URL to kanjidic2.xml(.gz)")
    args = parser.parse_args()

    xml_path = _resolve_source(args.kanjidic)
    jouyou: list[str] = []
    by_modern: dict[int, list[str]] = {1: [], 2: [], 4: []}

    for _event, char in ET.iterparse(str(xml_path)):
        if char.tag != "character":
            continue
        misc = char.find("misc")
        literal = char.findtext("literal") or ""
        grade = misc.findtext("grade") if misc is not None else None
        legacy = misc.findtext("jlpt") if misc is not None else None
        char.clear()
        if grade not in _JOUYOU_GRADES:
            continue
        jouyou.append(literal)
        modern = _LEGACY_TO_MODERN.get(legacy or "", 1)  # unlabelled Jouyou -> N1
        if modern in by_modern:
            by_modern[modern].append(literal)

    CHARSET_DIR.mkdir(parents=True, exist_ok=True)
    _write("joyo", jouyou)
    _write("n1", by_modern[1])
    _write("n2", by_modern[2])
    _write("n4", by_modern[4])
    print("n5.txt left as-is (hand-curated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
