"""View-model for the vocabulary browser tab."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from kanji_app.core.models import Vocab
from kanji_app.services.catalog import KanjiCatalog
from kanji_app.services.study import StudyService


class VocabViewModel(QObject):
    results_changed = Signal()
    selection_changed = Signal()
    deck_changed = Signal()

    def __init__(
        self,
        catalog: KanjiCatalog,
        study: StudyService | None = None,
        deck_id: int | None = None,
    ) -> None:
        super().__init__()
        self._catalog = catalog
        self._study = study
        self._deck_id = deck_id
        self._text = ""
        self._results: list[Vocab] = []
        self._selected: Vocab | None = None
        self.refresh()

    @property
    def results(self) -> list[Vocab]:
        return self._results

    @property
    def selected(self) -> Vocab | None:
        return self._selected

    @property
    def can_add_to_deck(self) -> bool:
        return self._study is not None and self._deck_id is not None

    @property
    def selected_in_deck(self) -> bool:
        if self._study is None or self._deck_id is None or self._selected is None:
            return False
        return self._study.is_vocab_in_deck(self._deck_id, self._selected.id)

    def kanji_literal(self, kanji_id: int) -> str | None:
        kanji = self._catalog.get(kanji_id)
        return kanji.literal if kanji is not None else None

    def set_text(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self.refresh()

    def select(self, vocab_id: int | None) -> None:
        self._selected = self._catalog.get_vocab(vocab_id) if vocab_id is not None else None
        self.selection_changed.emit()

    def set_deck(self, deck_id: int) -> None:
        self._deck_id = deck_id
        self.selection_changed.emit()

    def add_selected_to_deck(self) -> None:
        if (
            self._study is None
            or self._deck_id is None
            or self._selected is None
            or self.selected_in_deck
        ):
            return
        self._study.add_vocab(self._deck_id, self._selected.id)
        self.deck_changed.emit()
        self.selection_changed.emit()

    def refresh(self) -> None:
        self._results = self._catalog.browse_vocab(self._text)
        self.results_changed.emit()
        if self._selected and all(v.id != self._selected.id for v in self._results):
            self.select(None)
