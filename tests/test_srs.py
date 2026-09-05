from __future__ import annotations

from datetime import UTC, datetime, timedelta

from kanji_app.core.models import CardState, Rating
from kanji_app.core.srs import FsrsScheduler


def test_new_state_is_new_and_due_now() -> None:
    sched = FsrsScheduler()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    state = sched.new_state(now)
    assert state.state == CardState.NEW
    assert state.is_new
    assert state.reps == 0
    assert state.due == now


def test_first_review_advances_reps_and_sets_stability() -> None:
    sched = FsrsScheduler()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    result = sched.review(sched.new_state(now), Rating.GOOD, now)
    assert result.state.reps == 1
    assert result.state.stability is not None and result.state.stability > 0
    assert result.state.due > now
    assert result.state.state != CardState.NEW


def test_good_schedules_further_out_than_again() -> None:
    sched = FsrsScheduler()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    start = sched.new_state(now)
    again_due = sched.review(start, Rating.AGAIN, now).state.due
    good_due = sched.review(start, Rating.GOOD, now).state.due
    assert good_due > again_due


def test_lapse_counts_only_from_review_state() -> None:
    sched = FsrsScheduler()
    now = datetime(2026, 1, 1, tzinfo=UTC)

    state = sched.new_state(now)
    # Push the card to REVIEW with a few good answers.
    for _ in range(4):
        result = sched.review(state, Rating.GOOD, now)
        state = result.state
        now = state.due + timedelta(seconds=1)
    assert state.state == CardState.REVIEW
    assert state.lapses == 0

    lapsed = sched.review(state, Rating.AGAIN, now).state
    assert lapsed.lapses == 1
