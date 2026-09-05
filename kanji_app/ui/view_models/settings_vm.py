"""View-model for the Settings screen.

Each setter persists immediately (via :class:`StudyService`) and emits a signal
the view and the app shell listen to.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from kanji_app.services.settings import AppSettings
from kanji_app.services.study import StudyService


class SettingsViewModel(QObject):
    changed = Signal()
    theme_changed = Signal(str)

    def __init__(self, study: StudyService, deck_id: int) -> None:
        super().__init__()
        self._study = study
        self._deck_id = deck_id
        self._settings: AppSettings = study.settings
        deck = study.get_deck(deck_id)
        self._new_per_day = deck.new_per_day if deck else 10
        self._reviews_per_day = deck.reviews_per_day if deck else 200

    # -- state ------------------------------------------------------

    @property
    def theme(self) -> str:
        return self._settings.theme

    @property
    def fsrs_retention(self) -> float:
        return self._settings.fsrs_retention

    @property
    def new_per_day(self) -> int:
        return self._new_per_day

    @property
    def reviews_per_day(self) -> int:
        return self._reviews_per_day

    # -- commands -------------------------------------------------

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

    def set_new_per_day(self, value: int) -> None:
        if value != self._new_per_day:
            self._new_per_day = value
            self._study.update_deck(self._deck_id, new_per_day=value)
            self.changed.emit()

    def set_reviews_per_day(self, value: int) -> None:
        if value != self._reviews_per_day:
            self._reviews_per_day = value
            self._study.update_deck(self._deck_id, reviews_per_day=value)
            self.changed.emit()
