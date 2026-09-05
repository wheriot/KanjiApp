from __future__ import annotations

from kanji_app.services.study import StudyService
from kanji_app.ui.app import build_app
from kanji_app.ui.deck_controller import DeckController
from kanji_app.ui.main_window import MainWindow
from kanji_app.ui.view_models.decks_vm import DecksViewModel
from kanji_app.ui.views.decks_view import DecksView


def test_decks_vm_rows(study_service: StudyService) -> None:
    controller = DeckController(study_service)
    controller.create("Second")
    vm = DecksViewModel(controller)

    rows = vm.rows()
    assert [r.deck.name for r in rows] == ["My N5 Kanji", "Second"]
    assert rows[0].is_current
    assert vm.can_delete()


def test_decks_view_lists_and_edits(study_service: StudyService) -> None:
    build_app([])
    controller = DeckController(study_service)
    view = DecksView(DecksViewModel(controller))
    assert view._list.count() == 1

    view._name.setText("Kanji core")
    view._new_per_day.setValue(20)
    view._reviews_per_day.setValue(150)
    view._save_editor()

    assert controller.current.name == "Kanji core"
    assert controller.current.new_per_day == 20


def test_switching_deck_retargets_dashboard(study_service: StudyService) -> None:
    build_app([])
    catalog = None
    window = MainWindow(catalog=catalog, study=study_service)
    controller = window._decks
    assert controller is not None

    second = controller.create("Second")
    study_service.add_kanji(second.id, 1)
    study_service.add_kanji(second.id, 2)

    controller.select(second.id)
    assert window._dashboard is not None
    assert window._dashboard._vm.deck_name == "Second"
    assert window._dashboard._vm.new_available == 4
