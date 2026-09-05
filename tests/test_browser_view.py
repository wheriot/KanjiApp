from __future__ import annotations

import sqlite3

from kanji_app.services.catalog import KanjiCatalog
from kanji_app.ui.app import build_app
from kanji_app.ui.view_models.catalog_vm import CatalogViewModel
from kanji_app.ui.views.browser_view import BrowserView


def _view(conn: sqlite3.Connection) -> BrowserView:
    build_app([])
    return BrowserView(CatalogViewModel(KanjiCatalog(conn)))


def test_grid_populates_from_results(kanji_db: sqlite3.Connection) -> None:
    view = _view(kanji_db)
    labels = [view._grid.item(i).text() for i in range(view._grid.count())]
    assert labels == ["一", "水", "山"]


def test_selecting_a_grid_item_updates_detail(kanji_db: sqlite3.Connection) -> None:
    view = _view(kanji_db)
    row = next(i for i in range(view._grid.count()) if view._grid.item(i).text() == "水")
    view._grid.setCurrentRow(row)
    assert view._detail._literal.text() == "水"
    assert "4 strokes" in view._detail._meta.text()


def test_search_box_filters_grid(kanji_db: sqlite3.Connection) -> None:
    view = _view(kanji_db)
    view._search.setText("mountain")
    labels = [view._grid.item(i).text() for i in range(view._grid.count())]
    assert labels == ["山"]
