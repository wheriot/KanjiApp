from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from kanji_app.core.models import CardMode, CardState, Rating, SubjectType
from kanji_app.core.srs import FsrsScheduler
from kanji_app.data.repositories import CardRepo, DeckRepo, ReviewLogRepo

NOW = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


def test_deck_ensure_default_is_idempotent(conn: sqlite3.Connection) -> None:
    repo = DeckRepo(conn)
    first = repo.ensure_default()
    assert repo.ensure_default().id == first.id
    assert len(repo.all()) == 1
    assert first.new_per_day == 10


def test_card_create_roundtrip_and_update(conn: sqlite3.Connection) -> None:
    deck = DeckRepo(conn).ensure_default()
    cards = CardRepo(conn)
    sched = FsrsScheduler()

    card = cards.create(deck.id, SubjectType.KANJI, 42, CardMode.RECOGNITION, sched.new_state(NOW))
    assert card.scheduling.state == CardState.NEW
    assert cards.modes_for_subject(deck.id, SubjectType.KANJI, 42) == {CardMode.RECOGNITION}

    result = sched.review(card.scheduling, Rating.GOOD, NOW)
    cards.update_scheduling(card.id, result.state)

    reloaded = cards.get(card.id)
    assert reloaded is not None
    assert reloaded.scheduling.state != CardState.NEW
    assert reloaded.scheduling.reps == 1
    assert reloaded.scheduling.due > NOW
    assert reloaded.scheduling.last_reviewed_at is not None


def test_review_log_counts(conn: sqlite3.Connection) -> None:
    deck = DeckRepo(conn).ensure_default()
    cards = CardRepo(conn)
    log = ReviewLogRepo(conn)
    sched = FsrsScheduler()

    day_start = NOW - timedelta(hours=6)
    for subject in (1, 2):
        card = cards.create(
            deck.id, SubjectType.KANJI, subject, CardMode.RECOGNITION, sched.new_state(NOW)
        )
        first = sched.review(card.scheduling, Rating.GOOD, NOW)
        log.record(card.id, Rating.GOOD, first, NOW)
        second = sched.review(first.state, Rating.GOOD, NOW + timedelta(minutes=10))
        log.record(card.id, Rating.GOOD, second, NOW + timedelta(minutes=10))

    assert log.count_since(deck.id, day_start) == 4
    assert log.count_new_since(deck.id, day_start) == 2  # 2 cards' first reviews
    assert log.count_since(deck.id, NOW + timedelta(minutes=5)) == 2
