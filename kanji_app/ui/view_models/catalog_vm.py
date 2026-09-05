"""View-model for the kanji browser + detail screen.

Holds filter state and the current selection; talks to :class:`KanjiCatalog`.
Views observe the Qt signals and read the plain properties.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from kanji_app.core.kanjivg import StrokeDrawing
from kanji_app.core.models import Kanji
from kanji_app.services.catalog import FilterOptions, KanjiCatalog, KanjiFilter


class CatalogViewModel(QObject):
    results_changed = Signal()
    selection_changed = Signal()

    def __init__(self, catalog: KanjiCatalog) -> None:
        super().__init__()
        self._catalog = catalog
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
