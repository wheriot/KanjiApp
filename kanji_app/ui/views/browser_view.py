"""The Browse screen: filter controls, a grid of kanji, and the detail panel."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from kanji_app.ui.view_models.catalog_vm import CatalogViewModel
from kanji_app.ui.views.bulk_add import AddAllButton
from kanji_app.ui.views.kanji_detail_panel import KanjiDetailPanel

_ID_ROLE = Qt.ItemDataRole.UserRole


class BrowserView(QWidget):
    def __init__(self, vm: CatalogViewModel) -> None:
        super().__init__()
        self._vm = vm

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search kanji, meaning, or reading…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._vm.set_text)

        options = vm.filter_options()
        self._jlpt = _combo("JLPT", [(f"N{n}", n) for n in options.jlpt])
        self._jlpt.currentIndexChanged.connect(lambda: self._vm.set_jlpt(self._jlpt.currentData()))
        self._grade = _combo("Grade", [(f"Grade {n}", n) for n in options.grade])
        self._grade.currentIndexChanged.connect(
            lambda: self._vm.set_grade(self._grade.currentData())
        )
        self._strokes = _combo("Strokes", [(f"{n} strokes", n) for n in options.stroke_count])
        self._strokes.currentIndexChanged.connect(
            lambda: self._vm.set_stroke_count(self._strokes.currentData())
        )

        filters = QHBoxLayout()
        filters.addWidget(self._search, stretch=1)
        filters.addWidget(self._jlpt)
        filters.addWidget(self._grade)
        filters.addWidget(self._strokes)

        self._grid = QListWidget()
        self._grid.setViewMode(QListWidget.ViewMode.IconMode)
        self._grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._grid.setUniformItemSizes(True)
        self._grid.setGridSize(QSize(56, 56))
        self._grid.setSpacing(4)
        self._grid.setMovement(QListWidget.Movement.Static)
        self._grid.currentItemChanged.connect(self._on_current_item)

        self._count = QLabel()
        self._add_all = AddAllButton(
            "kanji",
            pending=self._vm.not_in_deck_count,
            add=self._vm.add_all_results_to_deck,
            can_add=lambda: self._vm.can_add_to_deck,
        )

        count_row = QHBoxLayout()
        count_row.addWidget(self._count)
        count_row.addStretch(1)
        count_row.addWidget(self._add_all)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addLayout(filters)
        left_layout.addWidget(self._grid, stretch=1)
        left_layout.addLayout(count_row)

        self._detail = KanjiDetailPanel()

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self._detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self._detail.add_requested.connect(self._vm.add_selected_to_deck)
        self._vm.results_changed.connect(self._reload_results)
        self._vm.selection_changed.connect(self._reload_detail)
        self._reload_results()

    # -- vm -> view -----------------------------------------------------

    def _reload_results(self) -> None:
        self._grid.blockSignals(True)
        self._grid.clear()
        for kanji in self._vm.results:
            item = QListWidgetItem(kanji.literal)
            item.setData(_ID_ROLE, kanji.id)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = item.font()
            font.setPointSize(22)
            item.setFont(font)
            self._grid.addItem(item)
        self._grid.blockSignals(False)
        self._count.setText(f"{len(self._vm.results)} kanji")
        self._add_all.refresh()

    def _reload_detail(self) -> None:
        self._detail.show_kanji(self._vm.selected, self._vm.drawing)
        self._detail.set_deck_state(
            can_add=self._vm.can_add_to_deck,
            in_deck=self._vm.selected_in_deck,
        )
        self._add_all.refresh()

    # -- view -> vm -----------------------------------------------------

    def _on_current_item(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        self._vm.select(current.data(_ID_ROLE) if current else None)


def _combo(any_label: str, values: list[tuple[str, int]]) -> QComboBox:
    combo = QComboBox()
    combo.addItem(f"Any {any_label.lower()}", None)
    for label, value in values:
        combo.addItem(label, value)
    return combo
