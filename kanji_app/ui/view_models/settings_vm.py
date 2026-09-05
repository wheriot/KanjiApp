"""View-model for the Settings screen (app-wide preferences only).

Each setter persists immediately (via :class:`StudyService`) and emits a signal
the view and the app shell listen to. Per-deck limits live on the Decks screen.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from kanji_app.services.settings import AppSettings
from kanji_app.services.study import StudyService


class SettingsViewModel(QObject):
    changed = Signal()
    theme_changed = Signal(str)

    def __init__(self, study: StudyService) -> None:
        super().__init__()
        self._study = study
        self._settings: AppSettings = study.settings

    @property
    def theme(self) -> str:
        return self._settings.theme

    @property
    def fsrs_retention(self) -> float:
        return self._settings.fsrs_retention

    def set_theme(self, theme: str) -> None:
        if theme != self._settings.theme:
            self._settings = self._study.update_settings(replace(self._settings, theme=theme))
            self.theme_changed.emit(self._settings.theme)
            self.changed.emit()

    def set_retention(self, retention: float) -> None:
        updated = self._study.update_settings(replace(self._settings, fsrs_retention=retention))
        if updated != self._settings:
            self._settings = updated
            self.changed.emit()
