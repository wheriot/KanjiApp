from __future__ import annotations

import sqlite3
from pathlib import Path

from kanji_app.core.models import ReadingType
from kanji_app.data.repositories import KanjiRepo
from scripts.import_kanjidic import import_kanjidic

SAMPLE = """<?xml version="1.0"?>
<kanjidic2>
  <character>
    <literal>水</literal>
    <misc>
      <grade>1</grade><stroke_count>4</stroke_count>
      <stroke_count>5</stroke_count><freq>223</freq><jlpt>4</jlpt>
    </misc>
    <reading_meaning>
      <rmgroup>
        <reading r_type="ja_on">スイ</reading>
        <reading r_type="ja_kun">みず</reading>
        <reading r_type="pinyin">shui3</reading>
        <meaning>water</meaning>
        <meaning m_lang="fr">eau</meaning>
      </rmgroup>
      <nanori>み</nanori>
    </reading_meaning>
  </character>
  <character>
    <literal>火</literal>
    <misc><grade>1</grade><stroke_count>4</stroke_count></misc>
    <reading_meaning><rmgroup><meaning>fire</meaning></rmgroup></reading_meaning>
  </character>
</kanjidic2>
"""


def _sample(tmp_path: Path) -> Path:
    path = tmp_path / "kanjidic2.xml"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def test_charset_filters_entries(conn: sqlite3.Connection, tmp_path: Path) -> None:
    count = import_kanjidic(_sample(tmp_path), conn, charset={"水"})
    assert count == 1
    assert KanjiRepo(conn).get_by_literal("火") is None


def test_parses_fields_readings_and_english_only(conn: sqlite3.Connection, tmp_path: Path) -> None:
    import_kanjidic(_sample(tmp_path), conn, charset=None)
    mizu = KanjiRepo(conn).get_by_literal("水")
    assert mizu is not None
    assert mizu.stroke_count == 4  # first stroke_count wins
    assert mizu.grade == 1
    assert mizu.jlpt_old == 4
    assert mizu.frequency == 223
    assert mizu.readings_of(ReadingType.ON) == ("スイ",)
    assert mizu.readings_of(ReadingType.KUN) == ("みず",)
    assert mizu.readings_of(ReadingType.NANORI) == ("み",)
    assert [m.value for m in mizu.meanings] == ["water"]  # French dropped


def test_reimport_replaces_readings(conn: sqlite3.Connection, tmp_path: Path) -> None:
    src = _sample(tmp_path)
    import_kanjidic(src, conn, charset={"水"})
    import_kanjidic(src, conn, charset={"水"})
    reading_count = conn.execute(
        "SELECT COUNT(*) FROM reading r JOIN kanji k ON k.id = r.kanji_id WHERE k.literal = '水'"
    ).fetchone()[0]
    assert reading_count == 3  # スイ / みず / み — not doubled
