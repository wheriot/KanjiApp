from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QPushButton

from kanji_app.core.models import CardMode, Rating
from kanji_app.services.settings import AppSettings
from kanji_app.services.study import StudyService
from kanji_app.ui.app import build_app
from kanji_app.ui.view_models.review_vm import ReviewViewModel
from kanji_app.ui.views.review_history_view import ReviewHistoryDialog
from kanji_app.ui.views.review_view import ReviewView, _elided


def _view(study: StudyService, with_kanji: int = 0) -> ReviewView:
    build_app([])
    deck = study.default_deck()
    for kid in range(1, with_kanji + 1):
        study.add_kanji(deck.id, kid)
    return ReviewView(ReviewViewModel(study, deck.id))


def test_idle_state_prompts_to_add_kanji(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=0)
    assert view._footer.currentIndex() == 0
    assert "Browse" in view._idle_label.text()
    assert view._start_button.isHidden()


def test_idle_state_offers_start_when_cards_waiting(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=1)
    assert not view._start_button.isHidden()
    assert "new card" in view._idle_label.text()
    assert view._reset_label.text() == ""


def test_idle_state_explains_the_daily_limit(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    study_service.update_deck(deck.id, new_per_day=2)
    for kid in range(1, 6):  # 5 kanji added, only 2 can start today
        study_service.add_kanji(deck.id, kid)
    build_app([])
    view = ReviewView(ReviewViewModel(study_service, deck.id))

    view._vm.start()
    for _ in range(4):  # answer the 2 kanji's 2 cards each
        view._vm.reveal()
        view._vm.answer(Rating.GOOD)

    text = view._idle_label.text()
    assert "Daily limit reached" in text
    assert "held back" in text
    assert view._start_button.isHidden()
    assert "reset in" in view._reset_label.text().lower()


def test_elided_shortens_long_text_but_leaves_short_text_alone() -> None:
    build_app([])
    button = QPushButton()
    button.setMaximumWidth(220)

    long_text = "a very long multiple-choice option that will not fit on one button" * 2
    shortened = _elided(button, long_text)
    assert shortened != long_text
    assert shortened.endswith("…")

    assert _elided(button, "short") == "short"


def test_choose_mode_buttons_carry_the_full_option_as_a_tooltip(
    study_service: StudyService,
) -> None:
    study_service.update_settings(AppSettings(review_input="choose"))
    view = _view(study_service, with_kanji=1)
    view._vm.start()
    item = view._vm.current
    assert item is not None

    for i, option in enumerate(item.options):
        assert view._choice_buttons[i].toolTip() == option


def test_copy_word_only_offered_once_the_headword_is_on_screen(
    study_service: StudyService,
) -> None:
    view = _view(study_service, with_kanji=1)
    view._vm.start()
    seen_modes = set()
    while (item := view._vm.current) is not None:
        seen_modes.add(item.card.mode)
        if item.card.mode == CardMode.RECALL:
            assert view._copy_button.isHidden()
        view._vm.reveal()
        assert not view._copy_button.isHidden()  # true for recognition, or recall once revealed
        view._vm.answer(Rating.GOOD)
    assert seen_modes == {CardMode.RECOGNITION, CardMode.RECALL}


def test_copy_word_puts_the_headword_on_the_clipboard(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=1)
    view._vm.start()
    while (item := view._vm.current) is not None and item.card.mode != CardMode.RECOGNITION:
        view._vm.reveal()
        view._vm.answer(Rating.GOOD)
    item = view._vm.current
    assert item is not None

    view._copy_word()

    clipboard = QGuiApplication.clipboard()
    assert clipboard is not None
    assert clipboard.text() == item.headword


def test_review_vm_exposes_history_and_deck_name(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=1)
    deck_name = view._vm.deck_name()
    assert deck_name == study_service.default_deck().name

    view._vm.start()
    item = view._vm.current
    assert item is not None
    view._vm.reveal()
    view._vm.answer(Rating.GOOD)

    history = view._vm.history()
    assert len(history) == 1
    assert history[0].headword == item.headword


def test_review_history_dialog_lists_the_answered_cards(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=1)
    view._vm.start()
    while view._vm.current is not None:
        view._vm.reveal()
        view._vm.answer(Rating.GOOD)

    dialog = ReviewHistoryDialog(view._vm.history(), "My Deck")
    assert dialog._table.rowCount() == 2  # recognition + recall
    words = [dialog._table.item(r, 0) for r in range(2)]
    assert all(w is not None and w.text() for w in words)  # word column populated


def test_flow_reveal_and_rate(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=1)
    view._vm.start()
    assert view._footer.currentIndex() == 1  # "show answer"

    view._vm.reveal()
    assert view._footer.currentIndex() == 2  # rating buttons
    assert "left" in view._status.text()

    view._vm.answer(Rating.GOOD)
    assert view._vm.answered == 1
    # back to a question or the completion page
    assert view._footer.currentIndex() in (0, 1)
