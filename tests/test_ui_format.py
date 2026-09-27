from __future__ import annotations

from datetime import UTC, datetime, timedelta

from kanji_app.ui.format import countdown, relative_time


def test_relative_time_buckets_by_magnitude() -> None:
    now = datetime.now(UTC)
    assert relative_time(now + timedelta(seconds=30)) == "in a moment"
    assert relative_time(now + timedelta(minutes=5)) == "in about 5 minutes"
    assert relative_time(now + timedelta(hours=5)) == "in about 5 hours"
    assert relative_time(now + timedelta(days=3)) == "in about 3 days"


def test_countdown_formats_hours_and_minutes() -> None:
    now = datetime.now(UTC)
    # a couple of seconds of buffer so the test isn't flaky across a minute boundary
    assert countdown(now + timedelta(hours=2, minutes=15, seconds=5)) == "2h 15m"
    assert countdown(now + timedelta(minutes=5, seconds=5)) == "5m"
    assert countdown(now + timedelta(seconds=10)) == "<1m"
    assert countdown(now - timedelta(minutes=5)) == "<1m"  # already passed, clamps at zero
