from __future__ import annotations

import sqlite3

import pytest

from kanji_app.services.catalog import KanjiCatalog
from kanji_app.services.study import StudyService
from kanji_app.ui.app import build_app
from kanji_app.ui.view_models.vocab_vm import VocabViewModel
from kanji_app.ui.views.vocab_browser_view import VocabBrowserView


@pytest.fixture
def vocab_catalog(kanji_db: sqlite3.Connection) -> KanjiCatalog:
    kanji_db.executescript(
        """
        INSERT INTO vocab (id, expression, kana, jlpt) VALUES (1, '水', 'みず', 5);
        INSERT INTO vocab_gloss (vocab_id, value) VALUES (1, 'water');
        INSERT INTO vocab_kanji (vocab_id, kanji_id) VALUES (1, 1);
        """
    )
    return KanjiCatalog(kanji_db)


def test_vocab_vm_search_and_select(vocab_catalog: KanjiCatalog) -> None:
    vm = VocabViewModel(vocab_catalog)
    assert [v.expression for v in vm.results] == ["水"]

    vm.select(1)
    assert vm.selected is not None and vm.selected.kana == "みず"
    assert vm.kanji_literal(1) == "水"

    vm.set_text("nothing matches xyz")
    assert vm.results == []
    assert vm.selected is None  # selection cleared when it leaves the results


def test_vocab_vm_add_to_deck(vocab_catalog: KanjiCatalog, study_service: StudyService) -> None:
    deck_id = study_service.default_deck().id
    vm = VocabViewModel(vocab_catalog, study_service, deck_id)
    vm.select(1)
    assert not vm.selected_in_deck

    added: list[bool] = []
    vm.deck_changed.connect(lambda: added.append(True))
    vm.add_selected_to_deck()

    assert added == [True]
    assert vm.selected_in_deck
    assert study_service.is_vocab_in_deck(deck_id, 1)


def test_vocab_browser_view_lists_and_shows_detail(vocab_catalog: KanjiCatalog) -> None:
    build_app([])
    view = VocabBrowserView(VocabViewModel(vocab_catalog))
    assert view._list.count() == 1

    view._list.setCurrentRow(0)
    assert view._expression.text() == "水"
    assert "water" in view._glosses.text()
    assert view._kanji.text() == "水"
