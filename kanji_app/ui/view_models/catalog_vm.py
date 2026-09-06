"""View-model for the kanji browser + detail screen.

Holds filter state and the current selection; talks to :class:`KanjiCatalog`.
Views observe the Qt signals and read the plain properties.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from kanji_app.core.kanjivg import StrokeDrawing
from kanji_app.core.models import Kanji, Vocab
from kanji_app.services.catalog import FilterOptions, KanjiCatalog, KanjiFilter
from kanji_app.services.study import StudyService


class CatalogViewModel(QObject):
    results_changed = Signal()
    selection_changed = Signal()
    deck_changed = Signal()  # a kanji was added to the study deck

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
        self._filter = KanjiFilter()
        self._results: list[Kanji] = []
        self._selected: Kanji | None = None
        self._drawing: StrokeDrawing | None = None
        self.refresh()

    # -- read-only state --------------------------------------------------

    @property
    def results(self) -> list[Kanji]:
        return self._results

    @property
    def filter(self) -> KanjiFilter:
        return self._filter

    @property
    def selected(self) -> Kanji | None:
        return self._selected

    @property
    def drawing(self) -> StrokeDrawing | None:
        return self._drawing

    def selected_words(self) -> list[Vocab]:
        if self._selected is None:
            return []
        return self._catalog.vocab_for_kanji(self._selected.id)

    @property
    def can_add_to_deck(self) -> bool:
        return self._study is not None and self._deck_id is not None

    @property
    def selected_in_deck(self) -> bool:
        if self._study is None or self._deck_id is None or self._selected is None:
            return False
        return self._study.is_in_deck(self._deck_id, self._selected.id)

    def filter_options(self) -> FilterOptions:
        return self._catalog.filter_options()

    # -- commands -------------------------------------------------------

    def set_text(self, text: str) -> None:
        self._apply(replace(self._filter, text=text))

    def set_jlpt(self, jlpt: int | None) -> None:
        self._apply(replace(self._filter, jlpt=jlpt))

    def set_grade(self, grade: int | None) -> None:
        self._apply(replace(self._filter, grade=grade))

    def set_stroke_count(self, stroke_count: int | None) -> None:
        self._apply(replace(self._filter, stroke_count=stroke_count))

    def select(self, kanji_id: int | None) -> None:
        if kanji_id is None:
            self._selected, self._drawing = None, None
        else:
            self._selected = self._catalog.get(kanji_id)
            self._drawing = self._catalog.stroke_drawing(kanji_id)
        self.selection_changed.emit()

    def set_deck(self, deck_id: int) -> None:
        self._deck_id = deck_id
        self.selection_changed.emit()  # refresh the detail panel's Add button

    def add_selected_to_deck(self) -> None:
        if (
            self._study is None
            or self._deck_id is None
            or self._selected is None
            or self.selected_in_deck
        ):
            return
        self._study.add_kanji(self._deck_id, self._selected.id)
        self.deck_changed.emit()
        self.selection_changed.emit()  # refresh the detail panel's Add button

    def not_in_deck_count(self) -> int:
        """How many of the current results aren't in the deck yet."""
        if self._study is None or self._deck_id is None:
            return 0
        return sum(1 for k in self._results if not self._study.is_in_deck(self._deck_id, k.id))

    def add_all_results_to_deck(self) -> int:
        """Add every current result to the deck. Returns kanji added."""
        return self._add_ids(k.id for k in self._results)

    def add_top_n_to_deck(self, n: int) -> int:
        """Add the N most frequent results not yet in the deck (results are freq-ordered)."""
        if self._study is None or self._deck_id is None:
            return 0
        wanted: list[int] = []
        for kanji in self._results:
            if not self._study.is_in_deck(self._deck_id, kanji.id):
                wanted.append(kanji.id)
            if len(wanted) >= n:
                break
        return self._add_ids(wanted)

    def _add_ids(self, ids: Iterable[int]) -> int:
        if self._study is None or self._deck_id is None:
            return 0
        pending = [i for i in ids if not self._study.is_in_deck(self._deck_id, i)]
        if not pending:
            return 0
        self._study.add_kanji_bulk(self._deck_id, pending)
        self.deck_changed.emit()
        self.selection_changed.emit()
        return len(pending)

    def refresh(self) -> None:
        self._results = self._catalog.browse(self._filter)
        self.results_changed.emit()
        if self._selected and all(k.id != self._selected.id for k in self._results):
            self.select(None)

    # -- internals ----------------------------------------------------

    def _apply(self, updated: KanjiFilter) -> None:
        if updated != self._filter:
            self._filter = updated
            self.refresh()
