"""Application settings, persisted in the study database's ``setting`` table."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace

from kanji_app.data.repositories import SettingsRepo

THEMES = ("system", "light", "dark")
REVIEW_INPUTS = ("reveal", "choose", "type")

_RETENTION_MIN = 0.80
_RETENTION_MAX = 0.97


@dataclass(frozen=True, slots=True)
class AppSettings:
    theme: str = "system"
    fsrs_retention: float = 0.90
    review_input: str = "reveal"

    def normalised(self) -> AppSettings:
        theme = self.theme if self.theme in THEMES else "system"
        retention = min(_RETENTION_MAX, max(_RETENTION_MIN, self.fsrs_retention))
        review_input = self.review_input if self.review_input in REVIEW_INPUTS else "reveal"
        return replace(
            self, theme=theme, fsrs_retention=round(retention, 2), review_input=review_input
        )


class SettingsStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._repo = SettingsRepo(conn)

    def load(self) -> AppSettings:
        raw = self._repo.all()
        defaults = AppSettings()
        return AppSettings(
            theme=raw.get("theme", defaults.theme),
            fsrs_retention=_as_float(raw.get("fsrs_retention"), defaults.fsrs_retention),
            review_input=raw.get("review_input", defaults.review_input),
        ).normalised()

    def save(self, settings: AppSettings) -> AppSettings:
        settings = settings.normalised()
        self._repo.set("theme", settings.theme)
        self._repo.set("fsrs_retention", f"{settings.fsrs_retention:.2f}")
        self._repo.set("review_input", settings.review_input)
        return settings


def _as_float(value: str | None, fallback: float) -> float:
    try:
        return float(value) if value is not None else fallback
    except ValueError:
        return fallback
