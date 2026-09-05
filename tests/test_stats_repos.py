from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from kanji_app.core.models import CardMode, CardState, Rating, SubjectType
from kanji_app.core.srs import FsrsScheduler
from kanji_app.data.repositories import CardRepo, DeckRepo, KanjiRepo, ReviewLogRepo

NOW = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)


def test_card_aggregates(conn: sqlite3.Connection) -> None:
    deck = DeckRepo(conn).ensure_default()
    cards = CardRepo(conn)
    sched = FsrsScheduler()

    a = cards.create(deck.id, SubjectType.KANJI, 1, CardMode.RECOGNITION, sched.new_state(NOW))
    cards.create(deck.id, SubjectType.KANJI, 1, CardMode.RECALL, sched.new_state(NOW))
    cards.update_scheduling(a.id, sched.review(a.scheduling, Rating.GOOD, NOW).state)

    assert cards.state_breakdown(deck.id) == {CardState.NEW: 1, CardState.LEARNING: 1}
    assert cards.subject_ids(deck.id) == {1}
    assert cards.subject_ids(deck.id, learned_only=True) == {1}

    due = cards.due_dates_between(deck.id, NOW, NOW + timedelta(days=1))
    assert len(due) == 1  # only the reviewed (non-new) card has a real due date window


def test_review_log_retention_and_timestamps(conn: sqlite3.Connection) -> None:
    deck = DeckRepo(conn).ensure_default()
    cards = CardRepo(conn)
    log = ReviewLogRepo(conn)
    sched = FsrsScheduler()

    card = cards.create(deck.id, SubjectType.KANJI, 1, CardMode.RECOGNITION, sched.new_state(NOW))
    first = sched.review(card.scheduling, Rating.AGAIN, NOW)
    log.record(card.id, Rating.AGAIN, first, NOW)  # prev_stability 0 -> not mature
    second = sched.review(first.state, Rating.GOOD, NOW + timedelta(minutes=5))
    log.record(card.id, Rating.GOOD, second, NOW + timedelta(minutes=5))
    third = sched.review(second.state, Rating.AGAIN, NOW + timedelta(minutes=10))
    log.record(card.id, Rating.AGAIN, third, NOW + timedelta(minutes=10))

    since = NOW - timedelta(days=1)
    assert len(log.timestamps_since(deck.id, since)) == 3
    passed, total = log.retention_since(deck.id, since)
    assert (passed, total) == (1, 2)  # 2 mature reviews, 1 was not "Again"


def test_kanji_jlpt_helpers(kanji_db: sqlite3.Connection) -> None:
    repo = KanjiRepo(kanji_db)
    assert repo.count_by_jlpt() == {5: 3}
    assert repo.jlpt_by_id([1, 2]) == {1: 5, 2: 5}
    assert repo.jlpt_by_id([]) == {}
