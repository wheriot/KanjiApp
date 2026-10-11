"""Dialog listing the deck's most recently answered reviews, newest first."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from kanji_app.services.study import ReviewHistoryRow
from kanji_app.ui.format import absolute_time

_COLUMNS = ("Word", "Meaning", "Type", "Mode", "Rating", "When", "Time")


class ReviewHistoryDialog(QDialog):
    def __init__(self, rows: list[ReviewHistoryRow], deck_name: str) -> None:
        super().__init__()
        self.setWindowTitle(f"Recent reviews in “{deck_name}”")
        self.resize(700, 480)

        count = QLabel(f"Last {len(rows)} review{'' if len(rows) == 1 else 's'}")
        header = QHBoxLayout()
        header.addWidget(count)
        header.addStretch(1)

        self._table = QTableWidget(len(rows), len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        for r, row in enumerate(rows):
            for c, text in enumerate(_row_cells(row)):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(r, c, item)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self._table)


def _row_cells(row: ReviewHistoryRow) -> tuple[str, str, str, str, str, str, str]:
    return (
        row.headword,
        row.gloss,
        row.subject_type.value.title(),
        row.mode.value.title(),
        row.log.rating.name.title(),
        absolute_time(row.log.reviewed_at),
        _elapsed_text(row.log.elapsed_ms),
    )


def _elapsed_text(elapsed_ms: int) -> str:
    return f"{elapsed_ms / 1000:.1f}s" if elapsed_ms else "—"
