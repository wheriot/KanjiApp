"""Statistics service: turns the study log into the numbers the UI shows.

Reads the writable study database and the reference kanji database (for JLPT
totals). Bucketing by "day" uses the same 04:00 boundary as the review queue.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from kanji_app.core.models import CardState
from kanji_app.core.review_session import day_start
from kanji_app.data.repositories import CardRepo, KanjiRepo, ReviewLogRepo

HISTORY_DAYS = 21
FORECAST_DAYS = 14


@dataclass(frozen=True, slots=True)
class DayCount:
    day: date
    count: int


@dataclass(frozen=True, slots=True)
class JlptProgress:
    level: int
    total: int
    in_deck: int
    learned: int


@dataclass(frozen=True, slots=True)
class StatsReport:
    reviewed_today: int
    streak_days: int
    retention: float | None  # None until there are mature reviews
    mature_reviews: int
    history: list[DayCount] = field(default_factory=list)
    forecast: list[DayCount] = field(default_factory=list)
    jlpt: list[JlptProgress] = field(default_factory=list)
    state_breakdown: dict[CardState, int] = field(default_factory=dict)
    total_cards: int = 0


class StatsService:
    def __init__(self, study_conn: sqlite3.Connection, reference_conn: sqlite3.Connection) -> None:
        self._cards = CardRepo(study_conn)
        self._log = ReviewLogRepo(study_conn)
        self._kanji = KanjiRepo(reference_conn)

    def report(self, deck_id: int, now: datetime | None = None) -> StatsReport:
        moment = now or datetime.now(UTC)
        today_start = day_start(moment)
        history_start = today_start - timedelta(days=HISTORY_DAYS - 1)

        timestamps = self._log.timestamps_since(deck_id, history_start)
        per_day = _bucket_by_day(timestamps, today_start, HISTORY_DAYS)

        passed, mature = self._log.retention_since(deck_id, history_start)
        retention = passed / mature if mature else None

        state_breakdown = self._cards.state_breakdown(deck_id)

        return StatsReport(
            reviewed_today=per_day[-1].count,
            streak_days=_streak(per_day),
            retention=retention,
            mature_reviews=mature,
            history=per_day,
            forecast=self._forecast(deck_id, today_start),
            jlpt=self._jlpt_progress(deck_id),
            state_breakdown=state_breakdown,
            total_cards=sum(state_breakdown.values()),
        )

    def _forecast(self, deck_id: int, today_start: datetime) -> list[DayCount]:
        end = today_start + timedelta(days=FORECAST_DAYS)
        due = self._cards.due_dates_between(deck_id, today_start, end)
        counts: Counter[date] = Counter(day_start(d).date() for d in due)
        return [
            DayCount(
                day=(today_start + timedelta(days=i)).date(),
                count=counts.get((today_start + timedelta(days=i)).date(), 0),
            )
            for i in range(FORECAST_DAYS)
        ]

    def _jlpt_progress(self, deck_id: int) -> list[JlptProgress]:
        totals = self._kanji.count_by_jlpt()
        in_deck_ids = self._cards.subject_ids(deck_id)
        learned_ids = self._cards.subject_ids(deck_id, learned_only=True)
        in_deck_levels = _levels(self._kanji.jlpt_by_id(in_deck_ids))
        learned_levels = _levels(self._kanji.jlpt_by_id(learned_ids))
        return [
            JlptProgress(
                level=level,
                total=total,
                in_deck=in_deck_levels.get(level, 0),
                learned=learned_levels.get(level, 0),
            )
            for level, total in sorted(totals.items(), reverse=True)
        ]


def _bucket_by_day(timestamps: list[datetime], today_start: datetime, days: int) -> list[DayCount]:
    counts: Counter[date] = Counter(day_start(ts).date() for ts in timestamps)
    start = today_start - timedelta(days=days - 1)
    return [
        DayCount(
            day=(start + timedelta(days=i)).date(),
            count=counts.get((start + timedelta(days=i)).date(), 0),
        )
        for i in range(days)
    ]


def _streak(per_day: list[DayCount]) -> int:
    """Consecutive days ending today (or yesterday) that have at least one review."""
    streak = 0
    for entry in reversed(per_day):
        if entry.count > 0:
            streak += 1
        elif streak == 0 and entry is per_day[-1]:
            continue  # today not studied yet — a streak can still run to yesterday
        else:
            break
    return streak


def _levels(by_id: dict[int, int | None]) -> dict[int, int]:
    counts: Counter[int] = Counter()
    for level in by_id.values():
        if level is not None:
            counts[level] += 1
    return dict(counts)
