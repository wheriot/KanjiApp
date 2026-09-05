"""View-model for the Dashboard screen."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from kanji_app.services.stats import StatsService
from kanji_app.services.study import StudyService, TodaySummary


class DashboardViewModel(QObject):
    changed = Signal()

    def __init__(self, study: StudyService, stats: StatsService, deck_id: int) -> None:
        super().__init__()
        self._study = study
        self._stats = stats
        self._deck_id = deck_id
        self._deck_name = ""
        self._summary = TodaySummary(0, 0, 0)
        self._streak = 0
        self.refresh()

    @property
    def deck_name(self) -> str:
        return self._deck_name

    @property
    def due(self) -> int:
        return self._summary.due

    @property
    def new_available(self) -> int:
        return self._summary.new_available

    @property
    def reviewed_today(self) -> int:
        return self._summary.reviewed_today

    @property
    def streak_days(self) -> int:
        return self._streak

    @property
    def has_work(self) -> bool:
        return self._summary.waiting > 0

    def refresh(self) -> None:
        deck = self._study.default_deck()
        self._deck_name = deck.name
        self._summary = self._study.today_summary(self._deck_id)
        self._streak = self._stats.report(self._deck_id).streak_days
        self.changed.emit()
