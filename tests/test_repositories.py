from __future__ import annotations

import sqlite3

from kanji_app.core.models import ReadingType
from kanji_app.data.repositories import KanjiRepo


def test_get_by_literal_hydrates_readings_and_meanings(kanji_db: sqlite3.Connection) -> None:
    repo = KanjiRepo(kanji_db)
    mizu = repo.get_by_literal("水")
    assert mizu is not None
    assert mizu.stroke_count == 4
    assert mizu.jlpt == 5
    assert mizu.jlpt_old == 4
    assert mizu.readings_of(ReadingType.ON) == ("スイ",)
    assert mizu.readings_of(ReadingType.KUN) == ("みず",)
    assert [m.value for m in mizu.meanings] == ["water"]


def test_get_by_literal_unknown_returns_none(kanji_db: sqlite3.Connection) -> None:
    assert KanjiRepo(kanji_db).get_by_literal("龘") is None


def test_find_by_jlpt_orders_known_frequency_first(kanji_db: sqlite3.Connection) -> None:
    literals = [k.literal for k in KanjiRepo(kanji_db).find(jlpt=5)]
    assert literals == ["一", "水", "山"]  # freq 2, 223, then NULL


def test_find_by_grade(kanji_db: sqlite3.Connection) -> None:
    assert len(KanjiRepo(kanji_db).find(grade=1)) == 3
    assert KanjiRepo(kanji_db).find(grade=2) == []


def test_find_combines_filters(kanji_db: sqlite3.Connection) -> None:
    repo = KanjiRepo(kanji_db)
    assert [k.literal for k in repo.find(jlpt=5, stroke_count=3)] == ["山"]
    assert [k.literal for k in repo.find(text="water", grade=1)] == ["水"]
    assert repo.find(text="water", stroke_count=99) == []


def test_distinct_values(kanji_db: sqlite3.Connection) -> None:
    repo = KanjiRepo(kanji_db)
    assert repo.distinct_values("stroke_count") == [1, 3, 4]
    assert repo.distinct_values("jlpt") == [5]


def test_search_matches_literal_meaning_and_reading(kanji_db: sqlite3.Connection) -> None:
    repo = KanjiRepo(kanji_db)
    assert [k.literal for k in repo.search("山")] == ["山"]
    assert [k.literal for k in repo.search("mountain")] == ["山"]
    assert [k.literal for k in repo.search("やま")] == ["山"]
    assert repo.search("   ") == []


def test_search_respects_limit(kanji_db: sqlite3.Connection) -> None:
    # every seeded kanji is grade 1 / jlpt 5, but only "one"/"single" share a gloss word
    results = KanjiRepo(kanji_db).search("s", limit=1)
    assert len(results) == 1


def test_stroke_svg(kanji_db: sqlite3.Connection) -> None:
    repo = KanjiRepo(kanji_db)
    ichi = repo.get_by_literal("一")
    assert ichi is not None
    assert repo.stroke_svg(1) == '<svg id="mizu"/>'
    assert repo.stroke_svg(ichi.id) is None  # 一 has no kanjivg row


def test_count(kanji_db: sqlite3.Connection) -> None:
    assert KanjiRepo(kanji_db).count() == 3
