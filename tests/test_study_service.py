from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from kanji_app.core.models import CardMode, Rating
from kanji_app.services.study import StudyService, open_study_service

NOON = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _first_kanji_ids(service: StudyService, n: int) -> list[int]:
    # ids 1..n exist in the shipped kanji.db
    return list(range(1, n + 1))


def test_add_kanji_creates_two_cards_and_is_idempotent(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    assert study_service.add_kanji(deck.id, 1, NOON) == 2
    assert study_service.add_kanji(deck.id, 1, NOON) == 0
    assert study_service.is_in_deck(deck.id, 1)


def test_start_session_returns_recognition_and_recall_items(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    study_service.add_kanji(deck.id, 1, NOON)
    modes = {item.card.mode for item in study_service.start_session(deck.id, NOON)}
    assert modes == {CardMode.RECOGNITION, CardMode.RECALL}


def test_new_card_daily_limit_is_enforced(study_service: StudyService) -> None:
    deck = study_service.default_deck()  # new_per_day = 10
    for kid in _first_kanji_ids(study_service, 8):  # 16 new cards
        study_service.add_kanji(deck.id, kid, NOON)

    session = study_service.start_session(deck.id, NOON)
    assert len(session) == 10

    for item in session:
        study_service.answer(item.card, Rating.GOOD, NOON)
    # limit is used up for the day even after restarting the queue
    assert study_service.start_session(deck.id, NOON) == []


def test_answer_persists_and_reschedules(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    study_service.add_kanji(deck.id, 1, NOON)
    item = study_service.start_session(deck.id, NOON)[0]

    study_service.answer(item.card, Rating.GOOD, NOON)

    later = NOON + timedelta(minutes=20)
    requeued = study_service.start_session(deck.id, later)
    same = next(i for i in requeued if i.card.id == item.card.id)
    assert same.card.scheduling.reps == 1
    assert same.card.scheduling.due > NOON


def test_progress_survives_reopen(tmp_path: Path) -> None:
    service = open_study_service(tmp_path)
    deck = service.default_deck()
    service.add_kanji(deck.id, 1, NOON)
    service.add_kanji(deck.id, 2, NOON)
    for item in service.start_session(deck.id, NOON):
        service.answer(item.card, Rating.GOOD, NOON)
    service.close()

    reopened = open_study_service(tmp_path)
    try:
        # same day: nothing new left, learning cards not yet due
        assert reopened.start_session(deck.id, NOON) == []
        # 20 minutes later the learning cards are due again
        later = NOON + timedelta(minutes=20)
        assert len(reopened.start_session(deck.id, later)) == 4
    finally:
        reopened.close()
