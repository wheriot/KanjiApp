"""Dialog listing every card currently in a deck — subject, mode, and SRS state."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from kanji_app.core.models import CardState
from kanji_app.services.study import CardPoolRow
from kanji_app.ui.format import relative_time

_COLUMNS = ("Word", "Meaning", "Type", "Mode", "State", "Due")
_STATE_FILTERS = ("All", "New", "Learning", "Review", "Relearning")


class CardPoolDialog(QDialog):
    def __init__(self, rows: list[CardPoolRow], deck_name: str) -> None:
        super().__init__()
        self._rows = rows
        self.setWindowTitle(f"Cards in “{deck_name}”")
        self.resize(640, 480)

        self._filter = QComboBox()
        self._filter.addItems(_STATE_FILTERS)
        self._filter.currentIndexChanged.connect(self._render)

        self._count = QLabel()

        header = QHBoxLayout()
        header.addWidget(QLabel("Show:"))
        header.addWidget(self._filter)
        header.addStretch(1)
        header.addWidget(self._count)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self._table)

        self._render()

    def _render(self) -> None:
        rows = self._filtered_rows()
        self._count.setText(f"{len(rows)} of {len(self._rows)} cards")

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, text in enumerate(_row_cells(row)):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(r, c, item)
        self._table.setSortingEnabled(True)

    def _filtered_rows(self) -> list[CardPoolRow]:
        choice = self._filter.currentText()
        if choice == "All":
            return self._rows
        return [r for r in self._rows if r.card.scheduling.state.value == choice.lower()]


def _row_cells(row: CardPoolRow) -> tuple[str, str, str, str, str, str]:
    return (
        row.headword,
        row.gloss,
        row.card.subject_type.value.title(),
        row.card.mode.value.title(),
        row.card.scheduling.state.value.title(),
        _due_text(row),
    )


def _due_text(row: CardPoolRow) -> str:
    if row.card.scheduling.state == CardState.NEW:
        return "—"
    due = row.card.scheduling.due
    if due <= datetime.now(UTC):
        return "Due now"
    return relative_time(due)
