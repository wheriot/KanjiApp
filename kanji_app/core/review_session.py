"""Building a study queue from a deck's cards.

Pure functions — no DB, no Qt. The service layer feeds in the deck's cards and
today's tallies; this decides what to study and in what order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from kanji_app.core.models import Card, CardState

DAY_START_HOUR = 4  # a review at 02:00 counts towards the previous day


def day_start(now: datetime, *, hour: int = DAY_START_HOUR) -> datetime:
    """Start of the current "study day" in local time, as an aware datetime."""
    local = now.astimezone()
    anchor = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if local < anchor:
        anchor -= timedelta(days=1)
    return anchor


def is_due(card: Card, now: datetime) -> bool:
    """A non-new card whose scheduled time has arrived."""
    return card.scheduling.state != CardState.NEW and card.scheduling.due <= now


@dataclass(frozen=True, slots=True)
class DeckCounts:
    """How many cards are waiting, before daily limits are applied."""

    due: int
    new: int

    @property
    def total(self) -> int:
        return self.due + self.new


def counts(cards: list[Card], now: datetime | None = None) -> DeckCounts:
    moment = now or datetime.now(UTC)
    due = sum(1 for c in cards if is_due(c, moment))
    new = sum(1 for c in cards if c.scheduling.state == CardState.NEW)
    return DeckCounts(due=due, new=new)


def build_queue(
    cards: list[Card],
    *,
    now: datetime | None = None,
    new_allowance: int,
    review_allowance: int,
) -> list[Card]:
    """Ordered cards to study now: due reviews first, then fresh cards.

    ``*_allowance`` is how many of each are still permitted today (daily limit
    minus what has already been done). Negative allowances clamp to zero.
    """
    moment = now or datetime.now(UTC)

    due = sorted(
        (c for c in cards if is_due(c, moment)),
        key=lambda c: c.scheduling.due,
    )[: max(0, review_allowance)]

    fresh = sorted(
        (c for c in cards if c.scheduling.state == CardState.NEW),
        key=lambda c: (c.created_at or moment, c.id),
    )[: max(0, new_allowance)]

    return [*due, *fresh]
