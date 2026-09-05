"""Shared "current deck" state for every study screen.

One instance is owned by :class:`MainWindow`; the study view-models subscribe to
its signals and re-target themselves when the selection changes.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from kanji_app.core.models import Deck
from kanji_app.services.study import StudyService


class DeckController(QObject):
    current_changed = Signal(int)  # newly selected deck id
    decks_changed = Signal()  # a deck was created / renamed / deleted

    def __init__(self, study: StudyService) -> None:
        super().__init__()
        self._study = study
        self._current = study.default_deck()

    # -- state ------------------------------------------------------

    @property
    def current(self) -> Deck:
        return self._current

    @property
    def current_id(self) -> int:
        return self._current.id

    def decks(self) -> list[Deck]:
        return self._study.decks()

    def card_count(self, deck_id: int) -> int:
        return self._study.deck_card_count(deck_id)

    # -- commands -------------------------------------------------

    def select(self, deck_id: int) -> None:
        if deck_id == self._current.id:
            return
        deck = self._study.get_deck(deck_id)
        if deck is not None:
            self._current = deck
            self.current_changed.emit(deck.id)

    def create(self, name: str) -> Deck:
        deck = self._study.create_deck(name.strip() or "New deck")
        self.decks_changed.emit()
        return deck

    def rename(self, deck_id: int, name: str) -> None:
        self._study.update_deck(deck_id, name=name.strip() or "Untitled deck")
        self._reload_current()
        self.decks_changed.emit()

    def set_limits(self, deck_id: int, *, new_per_day: int, reviews_per_day: int) -> None:
        self._study.update_deck(deck_id, new_per_day=new_per_day, reviews_per_day=reviews_per_day)
        self._reload_current()
        self.decks_changed.emit()

    def delete(self, deck_id: int) -> bool:
        """Delete a deck. Refuses to remove the last one. Returns whether it deleted."""
        if len(self.decks()) <= 1:
            return False
        self._study.delete_deck(deck_id)
        self.decks_changed.emit()
        if deck_id == self._current.id:
            self._current = self._study.default_deck()
            self.current_changed.emit(self._current.id)
        return True

    # -- internals ----------------------------------------------

    def _reload_current(self) -> None:
        refreshed = self._study.get_deck(self._current.id)
        if refreshed is not None:
            self._current = refreshed
