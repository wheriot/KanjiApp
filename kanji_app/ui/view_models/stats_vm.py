"""View-model for the Stats screen."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from kanji_app.services.stats import StatsReport, StatsService


class StatsViewModel(QObject):
    changed = Signal()

    def __init__(self, stats: StatsService, deck_id: int) -> None:
        super().__init__()
        self._stats = stats
        self._deck_id = deck_id
        self._report = StatsReport(
            reviewed_today=0, streak_days=0, retention=None, mature_reviews=0
        )
        self.refresh()

    @property
    def report(self) -> StatsReport:
        return self._report

    def refresh(self) -> None:
        self._report = self._stats.report(self._deck_id)
        self.changed.emit()
