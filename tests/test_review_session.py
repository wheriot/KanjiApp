from __future__ import annotations

from datetime import UTC, datetime, timedelta

from kanji_app.core import review_session
from kanji_app.core.models import Card, CardMode, CardState, SchedulingState, SubjectType

NOON = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _card(card_id: int, state: CardState, due: datetime, *, created: datetime = NOON) -> Card:
    return Card(
        id=card_id,
        deck_id=1,
        subject_type=SubjectType.KANJI,
        subject_id=card_id,
        mode=CardMode.RECOGNITION,
        scheduling=SchedulingState(
            state=state,
            step=0,
            due=due,
            stability=None if state == CardState.NEW else 5.0,
            difficulty=None if state == CardState.NEW else 5.0,
            reps=0 if state == CardState.NEW else 3,
            lapses=0,
        ),
        created_at=created,
    )


def test_day_start_uses_configured_hour() -> None:
    before = datetime(2026, 1, 15, 2, 0, tzinfo=UTC).astimezone()
    after = datetime(2026, 1, 15, 9, 0, tzinfo=UTC).astimezone()
    assert review_session.day_start(before, hour=4) < before
    start = review_session.day_start(after, hour=4)
    assert start <= after and start.hour == 4


def test_is_due_ignores_new_and_future() -> None:
    assert review_session.is_due(_card(1, CardState.REVIEW, NOON - timedelta(days=1)), NOON)
    assert not review_session.is_due(_card(2, CardState.REVIEW, NOON + timedelta(days=1)), NOON)
    assert not review_session.is_due(_card(3, CardState.NEW, NOON - timedelta(days=1)), NOON)


def test_counts() -> None:
    cards = [
        _card(1, CardState.REVIEW, NOON - timedelta(hours=1)),
        _card(2, CardState.REVIEW, NOON + timedelta(hours=1)),
        _card(3, CardState.NEW, NOON),
        _card(4, CardState.NEW, NOON),
    ]
    assert review_session.counts(cards, NOON) == review_session.DeckCounts(due=1, new=2)


def test_build_queue_orders_due_first_then_new_and_applies_allowances() -> None:
    cards = [
        _card(1, CardState.NEW, NOON, created=NOON - timedelta(minutes=1)),
        _card(2, CardState.NEW, NOON, created=NOON),
        _card(3, CardState.REVIEW, NOON - timedelta(hours=2)),
        _card(4, CardState.REVIEW, NOON - timedelta(hours=5)),
    ]
    queue = review_session.build_queue(cards, now=NOON, new_allowance=1, review_allowance=5)
    assert [c.id for c in queue] == [4, 3, 1]  # oldest-due reviews first, then 1 new


def test_build_queue_clamps_negative_allowance() -> None:
    cards = [_card(3, CardState.REVIEW, NOON - timedelta(hours=1))]
    assert review_session.build_queue(cards, now=NOON, new_allowance=-5, review_allowance=-1) == []
