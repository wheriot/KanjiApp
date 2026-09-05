from __future__ import annotations

import sqlite3

from kanji_app.services.catalog import KanjiCatalog, KanjiFilter


def test_browse_with_empty_filter_returns_all(kanji_db: sqlite3.Connection) -> None:
    catalog = KanjiCatalog(kanji_db)
    assert [k.literal for k in catalog.browse(KanjiFilter())] == ["一", "水", "山"]


def test_browse_applies_filter(kanji_db: sqlite3.Connection) -> None:
    catalog = KanjiCatalog(kanji_db)
    assert [k.literal for k in catalog.browse(KanjiFilter(stroke_count=4))] == ["水"]
    assert [k.literal for k in catalog.browse(KanjiFilter(text="mountain"))] == ["山"]


def test_filter_options(kanji_db: sqlite3.Connection) -> None:
    options = KanjiCatalog(kanji_db).filter_options()
    assert options.jlpt == [5]
    assert options.grade == [1]
    assert options.stroke_count == [1, 3, 4]


def test_stroke_drawing(kanji_db: sqlite3.Connection) -> None:
    catalog = KanjiCatalog(kanji_db)
    mizu = catalog.browse(KanjiFilter(text="水"))[0]
    drawing = catalog.stroke_drawing(mizu.id)
    assert drawing is not None and drawing.stroke_count == 0  # fixture svg has no paths

    ichi = catalog.browse(KanjiFilter(text="一"))[0]
    assert catalog.stroke_drawing(ichi.id) is None  # no kanjivg row
