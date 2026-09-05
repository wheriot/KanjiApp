from __future__ import annotations

from kanji_app.services.study import StudyService
from kanji_app.ui.deck_controller import DeckController


def test_starts_on_default_deck(study_service: StudyService) -> None:
    controller = DeckController(study_service)
    assert controller.current.name == "My N5 Kanji"
    assert len(controller.decks()) == 1


def test_create_and_select_emits(study_service: StudyService) -> None:
    controller = DeckController(study_service)
    selected: list[int] = []
    controller.current_changed.connect(selected.append)

    deck = controller.create("Vocab")
    assert [d.name for d in controller.decks()] == ["My N5 Kanji", "Vocab"]

    controller.select(deck.id)
    assert controller.current_id == deck.id
    assert selected == [deck.id]

    controller.select(deck.id)  # no-op, already current
    assert selected == [deck.id]


def test_rename_and_set_limits(study_service: StudyService) -> None:
    controller = DeckController(study_service)
    deck_id = controller.current_id
    controller.rename(deck_id, "  Renamed  ")
    controller.set_limits(deck_id, new_per_day=15, reviews_per_day=300)

    assert controller.current.name == "Renamed"
    assert controller.current.new_per_day == 15
    assert controller.current.reviews_per_day == 300


def test_delete_guards_last_deck_and_reselects(study_service: StudyService) -> None:
    controller = DeckController(study_service)
    original = controller.current_id
    other = controller.create("Scratch")

    assert controller.delete(original) is True
    assert controller.current_id == other.id  # fell back to the survivor
    assert controller.delete(other.id) is False  # can't remove the last one
