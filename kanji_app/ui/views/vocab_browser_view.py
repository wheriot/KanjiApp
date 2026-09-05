"""The vocabulary tab of the Browse screen: search a word, inspect it, add it."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from kanji_app.ui.view_models.vocab_vm import VocabViewModel

_ID_ROLE = Qt.ItemDataRole.UserRole


class VocabBrowserView(QWidget):
    def __init__(self, vm: VocabViewModel) -> None:
        super().__init__()
        self._vm = vm

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search word, reading, or meaning…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._vm.set_text)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_current_item)
        self._count = QLabel()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._search)
        left_layout.addWidget(self._list, stretch=1)
        left_layout.addWidget(self._count)

        self._expression = QLabel()
        expr_font = self._expression.font()
        expr_font.setPointSize(32)
        self._expression.setFont(expr_font)
        self._kana = QLabel()
        self._glosses = QLabel()
        self._glosses.setWordWrap(True)
        self._kanji = QLabel()
        self._kanji.setWordWrap(True)

        self._add = QPushButton()
        self._add.clicked.connect(self._vm.add_selected_to_deck)
        self._add.hide()

        self._detail = QWidget()
        form = QFormLayout(self._detail)
        form.addRow(self._expression)
        form.addRow("Reading", self._kana)
        form.addRow("Meaning", self._glosses)
        form.addRow("Kanji", self._kanji)
        form.addRow(self._add)

        self._placeholder = QLabel("Select a word to see its details.")
        self._placeholder.setEnabled(False)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._placeholder)
        right_layout.addWidget(self._detail)
        right_layout.addStretch(1)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self._vm.results_changed.connect(self._reload_results)
        self._vm.selection_changed.connect(self._reload_detail)
        self._reload_results()
        self._reload_detail()

    def _reload_results(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for vocab in self._vm.results:
            item = QListWidgetItem(f"{vocab.expression}    {vocab.kana}")
            item.setData(_ID_ROLE, vocab.id)
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._count.setText(f"{len(self._vm.results)} words")

    def _reload_detail(self) -> None:
        vocab = self._vm.selected
        self._detail.setVisible(vocab is not None)
        self._placeholder.setVisible(vocab is None)
        if vocab is None:
            return
        self._expression.setText(vocab.expression)
        self._kana.setText(vocab.kana)
        self._glosses.setText("; ".join(vocab.glosses))
        self._kanji.setText(" ".join(self._kanji_literals(vocab.kanji_ids)) or "—")
        self._add.setVisible(self._vm.can_add_to_deck)
        self._add.setEnabled(self._vm.can_add_to_deck and not self._vm.selected_in_deck)
        self._add.setText("In study deck ✓" if self._vm.selected_in_deck else "Add to study deck")

    def _kanji_literals(self, ids: tuple[int, ...]) -> list[str]:
        return [lit for kid in ids if (lit := self._vm.kanji_literal(kid)) is not None]

    def _on_current_item(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        self._vm.select(current.data(_ID_ROLE) if current else None)
