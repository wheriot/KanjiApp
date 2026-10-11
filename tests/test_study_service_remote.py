"""StudyService features the phone server relies on (also used by the desktop)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from kanji_app.core.models import Rating
from kanji_app.core.romaji import to_romaji
from kanji_app.services.settings import AppSettings
from kanji_app.services.study import StudyService, open_study_service

NOON = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def test_next_item_is_the_head_of_the_session_queue(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    assert study_service.next_item(deck.id, NOON) is None

    study_service.add_kanji(deck.id, 1, NOON)
    study_service.add_kanji(deck.id, 2, NOON)
    session = study_service.start_session(deck.id, NOON)
    head = study_service.next_item(deck.id, NOON)
    assert head is not None
    assert head.card.id == session[0].card.id


def test_answer_card_schedules_from_the_stored_state_not_a_stale_copy(
    study_service: StudyService,
) -> None:
    deck = study_service.default_deck()
    study_service.add_kanji(deck.id, 1, NOON)
    stale = study_service.start_session(deck.id, NOON)[0].card

    # answered once on "the phone", then again from the desktop's old queue copy
    study_service.answer_card(stale.id, Rating.GOOD, NOON)
    study_service.answer(stale, Rating.GOOD, NOON + timedelta(minutes=1))

    reloaded = next(r.card for r in study_service.deck_cards(deck.id) if r.card.id == stale.id)
    assert reloaded.scheduling.reps == 2  # the second review built on the first


def test_answer_card_reports_a_missing_card(study_service: StudyService) -> None:
    assert study_service.answer_card(999_999, Rating.GOOD, NOON) is False


def test_submit_answer_grades_choose_mode_by_option_text(study_service: StudyService) -> None:
    study_service.update_settings(AppSettings(review_input="choose"))
    deck = study_service.default_deck()
    study_service.add_kanji(deck.id, 1, NOON)
    item = study_service.next_item(deck.id, NOON)
    assert item is not None
    wrong = next(o for o in item.options if o != item.answer)

    miss = study_service.submit_answer(item.card.id, wrong, NOON)
    assert miss is not None and miss.correct is False

    hit = study_service.submit_answer(item.card.id, item.answer, NOON + timedelta(minutes=1))
    assert hit is not None and hit.correct is True
    history = study_service.review_history(deck.id)
    assert [h.log.rating for h in history] == [Rating.GOOD, Rating.AGAIN]


def test_submit_answer_grades_type_mode_by_reading(study_service: StudyService) -> None:
    study_service.update_settings(AppSettings(review_input="type"))
    deck = study_service.default_deck()
    study_service.add_kanji(deck.id, 1, NOON)
    item = study_service.next_item(deck.id, NOON)
    assert item is not None and item.accepted

    result = study_service.submit_answer(item.card.id, to_romaji(item.accepted[0]), NOON)
    assert result is not None and result.correct is True
    assert result.item.answer  # the full card comes back for the reveal


def test_current_deck_persists_and_falls_back_to_the_default(tmp_path: Path) -> None:
    first = open_study_service(tmp_path)
    try:
        second = first.create_deck("Vocab")
        assert first.current_deck().id == first.default_deck().id
        first.set_current_deck(second.id)
    finally:
        first.close()

    reopened = open_study_service(tmp_path)
    try:
        assert reopened.current_deck().id == second.id
        reopened.delete_deck(second.id)
        assert reopened.current_deck().id == reopened.default_deck().id
    finally:
        reopened.close()


def test_reload_settings_picks_up_changes_from_another_process(tmp_path: Path) -> None:
    desktop = open_study_service(tmp_path)
    server = open_study_service(tmp_path)
    try:
        desktop.update_settings(AppSettings(review_input="type"))
        assert server.settings.review_input == "reveal"  # cached until reloaded
        assert server.reload_settings().review_input == "type"
    finally:
        desktop.close()
        server.close()
