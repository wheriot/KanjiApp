"""Small text-formatting helpers shared by views. No Qt, no state."""

from __future__ import annotations

from datetime import UTC, datetime


def relative_time(when: datetime) -> str:
    """Approximate human phrasing: "in about 3 hours", "in a moment"."""
    seconds = (when - datetime.now(UTC)).total_seconds()
    if seconds <= 90:
        return "in a moment"
    minutes = seconds / 60
    if minutes < 90:
        return f"in about {round(minutes)} minutes"
    hours = minutes / 60
    if hours < 36:
        return f"in about {round(hours)} hours"
    return f"in about {round(hours / 24)} days"


def absolute_time(when: datetime) -> str:
    """Local wall-clock time for a past event, e.g. "2026-09-27 14:32"."""
    return when.astimezone().strftime("%Y-%m-%d %H:%M")


def countdown(until: datetime) -> str:
    """Precise "Xh Ym" remaining until ``until`` (clamped at zero)."""
    seconds = max(0, int((until - datetime.now(UTC)).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return "<1m"
