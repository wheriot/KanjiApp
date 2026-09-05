from __future__ import annotations

import sqlite3

from kanji_app.services.catalog import KanjiCatalog
from kanji_app.ui.view_models.catalog_vm import CatalogViewModel


def _vm(conn: sqlite3.Connection) -> CatalogViewModel:
    return CatalogViewModel(KanjiCatalog(conn))


def test_initial_results_are_unfiltered(kanji_db: sqlite3.Connection) -> None:
    vm = _vm(kanji_db)
    assert [k.literal for k in vm.results] == ["一", "水", "山"]


def test_set_filter_refreshes_and_signals(kanji_db: sqlite3.Connection) -> None:
    vm = _vm(kanji_db)
    seen: list[int] = []
    vm.results_changed.connect(lambda: seen.append(len(vm.results)))

    vm.set_stroke_count(4)
    assert [k.literal for k in vm.results] == ["水"]
    assert seen == [1]

    vm.set_stroke_count(4)  # unchanged -> no extra signal
    assert seen == [1]


def test_selection_loads_kanji_and_drawing(kanji_db: sqlite3.Connection) -> None:
    vm = _vm(kanji_db)
    fired: list[str] = []
    vm.selection_changed.connect(lambda: fired.append(vm.selected.literal if vm.selected else "-"))

    mizu_id = next(k.id for k in vm.results if k.literal == "水")
    vm.select(mizu_id)
    assert vm.selected is not None and vm.selected.literal == "水"
    assert vm.drawing is not None
    assert fired == ["水"]


def test_filtering_out_selection_clears_it(kanji_db: sqlite3.Connection) -> None:
    vm = _vm(kanji_db)
    mizu_id = next(k.id for k in vm.results if k.literal == "水")
    vm.select(mizu_id)
    vm.set_stroke_count(3)  # 山 only; 水 drops out
    assert vm.selected is None
