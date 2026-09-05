"""Spaced-repetition scheduling.

The rest of the app talks to the :class:`Scheduler` protocol and never imports
``fsrs`` directly. :class:`FsrsScheduler` is the only place that knows about the
FSRS library, so the algorithm stays swappable and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import fsrs

from kanji_app.core.models import CardState, Rating, SchedulingState

_TO_FSRS_STATE = {
    CardState.NEW: fsrs.State.Learning,
    CardState.LEARNING: fsrs.State.Learning,
    CardState.REVIEW: fsrs.State.Review,
    CardState.RELEARNING: fsrs.State.Relearning,
}
_FROM_FSRS_STATE = {
    fsrs.State.Learning: CardState.LEARNING,
    fsrs.State.Review: CardState.REVIEW,
    fsrs.State.Relearning: CardState.RELEARNING,
}


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """Outcome of grading one review: the new state plus what changed."""

    state: SchedulingState
    previous_due: datetime
    previous_stability: float
    new_stability: float


class Scheduler(Protocol):
    """Everything the app needs from an SRS engine."""

    def new_state(self, now: datetime | None = None) -> SchedulingState:
        """Scheduling state for a freshly created, never-reviewed card."""
        ...

    def review(
        self,
        state: SchedulingState,
        rating: Rating,
        now: datetime | None = None,
    ) -> ReviewResult:
        """Grade a review and return the updated scheduling state."""
        ...


class FsrsScheduler:
    """:class:`Scheduler` backed by the FSRS algorithm.

    ``desired_retention`` is the probability of recall we aim for at review time
    (0.9 = remember 90% of due cards).
    """

    def __init__(self, desired_retention: float = 0.9) -> None:
        self._engine = fsrs.Scheduler(desired_retention=desired_retention)

    def new_state(self, now: datetime | None = None) -> SchedulingState:
        moment = _utc(now)
        return SchedulingState(
            state=CardState.NEW,
            step=0,
            due=moment,
            stability=None,
            difficulty=None,
            reps=0,
            lapses=0,
            last_reviewed_at=None,
        )

    def review(
        self,
        state: SchedulingState,
        rating: Rating,
        now: datetime | None = None,
    ) -> ReviewResult:
        moment = _utc(now)
        card = self._to_card(state, fallback_due=moment)
        updated, _log = self._engine.review_card(
            card, fsrs.Rating(int(rating)), review_datetime=moment
        )

        lapsed = rating == Rating.AGAIN and state.state == CardState.REVIEW
        new_state = SchedulingState(
            state=_FROM_FSRS_STATE[updated.state],
            step=updated.step or 0,
            due=updated.due,
            stability=updated.stability,
            difficulty=updated.difficulty,
            reps=state.reps + 1,
            lapses=state.lapses + (1 if lapsed else 0),
            last_reviewed_at=moment,
        )
        return ReviewResult(
            state=new_state,
            previous_due=state.due,
            previous_stability=state.stability or 0.0,
            new_stability=updated.stability or 0.0,
        )

    def _to_card(self, state: SchedulingState, fallback_due: datetime) -> fsrs.Card:
        return fsrs.Card(
            state=_TO_FSRS_STATE[state.state],
            step=state.step,
            stability=state.stability,
            difficulty=state.difficulty,
            due=state.due or fallback_due,
            last_review=state.last_reviewed_at,
        )


def _utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    return now if now.tzinfo else now.replace(tzinfo=UTC)
