"""View-model for the Decks screen."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from kanji_app.core.models import Deck
from kanji_app.ui.deck_controller import DeckController


@dataclass(frozen=True, slots=True)
class DeckRow:
    deck: Deck
    card_count: int
    is_current: bool


class DecksViewModel(QObject):
    changed = Signal()

    def __init__(self, controller: DeckController) -> None:
        super().__init__()
        self._controller = controller
        controller.decks_changed.connect(self.changed)
        controller.current_changed.connect(lambda _id: self.changed.emit())

    def rows(self) -> list[DeckRow]:
        current_id = self._controller.current_id
        return [
            DeckRow(
                deck=deck,
                card_count=self._controller.card_count(deck.id),
                is_current=deck.id == current_id,
            )
            for deck in self._controller.decks()
        ]

    def can_delete(self) -> bool:
        return len(self._controller.decks()) > 1

    def create(self, name: str) -> None:
        self._controller.create(name)

    def save(self, deck_id: int, *, name: str, new_per_day: int, reviews_per_day: int) -> None:
        self._controller.rename(deck_id, name)
        self._controller.set_limits(
            deck_id, new_per_day=new_per_day, reviews_per_day=reviews_per_day
        )

    def make_current(self, deck_id: int) -> None:
        self._controller.select(deck_id)

    def delete(self, deck_id: int) -> bool:
        return self._controller.delete(deck_id)
