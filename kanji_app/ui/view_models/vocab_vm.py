"""View-model for the vocabulary browser tab."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from kanji_app.core.models import Sentence, Vocab
from kanji_app.services.catalog import FilterOptions, KanjiCatalog, VocabFilter
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
        self._filter = VocabFilter()
        self._results: list[Vocab] = []
        self._selected: Vocab | None = None
        self.refresh()

    def filter_options(self) -> FilterOptions:
        return self._catalog.vocab_filter_options()

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

    def selected_sentences(self) -> list[Sentence]:
        if self._selected is None:
            return []
        return self._catalog.vocab_sentences(self._selected.id)

    def set_text(self, text: str) -> None:
        self._apply(replace(self._filter, text=text))

    def set_jlpt(self, jlpt: int | None) -> None:
        self._apply(replace(self._filter, jlpt=jlpt))

    def set_grade(self, grade: int | None) -> None:
        self._apply(replace(self._filter, grade=grade))

    def _apply(self, updated: VocabFilter) -> None:
        if updated != self._filter:
            self._filter = updated
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

    def not_in_deck_count(self) -> int:
        if self._study is None or self._deck_id is None:
            return 0
        return sum(
            1 for v in self._results if not self._study.is_vocab_in_deck(self._deck_id, v.id)
        )

    def add_all_results_to_deck(self) -> int:
        return self._add_ids(v.id for v in self._results)

    def add_top_n_to_deck(self, n: int) -> int:
        if self._study is None or self._deck_id is None:
            return 0
        wanted: list[int] = []
        for vocab in self._results:
            if not self._study.is_vocab_in_deck(self._deck_id, vocab.id):
                wanted.append(vocab.id)
            if len(wanted) >= n:
                break
        return self._add_ids(wanted)

    def _add_ids(self, ids: Iterable[int]) -> int:
        if self._study is None or self._deck_id is None:
            return 0
        pending = [i for i in ids if not self._study.is_vocab_in_deck(self._deck_id, i)]
        if not pending:
            return 0
        self._study.add_vocab_bulk(self._deck_id, pending)
        self.deck_changed.emit()
        self.selection_changed.emit()
        return len(pending)

    def refresh(self) -> None:
        self._results = self._catalog.browse_vocab(self._filter)
        self.results_changed.emit()
        if self._selected and all(v.id != self._selected.id for v in self._results):
            self.select(None)
