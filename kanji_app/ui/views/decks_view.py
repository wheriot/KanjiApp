"""The Decks screen: create, rename, re-limit, switch and delete study decks."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from kanji_app.ui.view_models.decks_vm import DecksViewModel

_ID_ROLE = Qt.ItemDataRole.UserRole


class DecksView(QWidget):
    def __init__(self, vm: DecksViewModel) -> None:
        super().__init__()
        self._vm = vm

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._load_editor)

        new_button = QPushButton("New deck…")
        new_button.clicked.connect(self._create_deck)

        left = QVBoxLayout()
        left.addWidget(self._list, stretch=1)
        left.addWidget(new_button)

        self._name = QLineEdit()
        self._new_per_day = QSpinBox()
        self._new_per_day.setRange(0, 999)
        self._reviews_per_day = QSpinBox()
        self._reviews_per_day.setRange(0, 9999)

        self._save = QPushButton("Save")
        self._save.clicked.connect(self._save_editor)
        self._make_current = QPushButton("Make current")
        self._make_current.clicked.connect(self._make_current_deck)
        self._delete = QPushButton("Delete")
        self._delete.clicked.connect(self._delete_deck)

        editor_buttons = QHBoxLayout()
        editor_buttons.addWidget(self._save)
        editor_buttons.addWidget(self._make_current)
        editor_buttons.addStretch(1)
        editor_buttons.addWidget(self._delete)

        self._editor = QWidget()
        form = QFormLayout(self._editor)
        form.addRow("Name", self._name)
        form.addRow("New cards per day", self._new_per_day)
        form.addRow("Reviews per day", self._reviews_per_day)
        form.addRow(editor_buttons)

        self._empty = QLabel("Select a deck to edit it.")
        self._empty.setEnabled(False)

        right = QVBoxLayout()
        right.addWidget(self._empty)
        right.addWidget(self._editor)
        right.addStretch(1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addLayout(left, stretch=1)
        layout.addLayout(right, stretch=2)

        self._vm.changed.connect(self._reload)
        self._reload()

    # -- rendering -----------------------------------------------

    def refresh(self) -> None:
        self._reload()

    def _reload(self) -> None:
        selected = self._current_deck_id()
        self._list.blockSignals(True)
        self._list.clear()
        for row in self._vm.rows():
            label = f"{row.deck.name}  ·  {row.card_count} cards"
            if row.is_current:
                label += "   ★"
            item = QListWidgetItem(label)
            item.setData(_ID_ROLE, row.deck.id)
            self._list.addItem(item)
            if row.deck.id == selected:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)
        if self._current_deck_id() is None and self._list.count():
            self._list.setCurrentRow(0)
        self._load_editor(self._list.currentItem(), None)

    def _load_editor(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        self._editor.setVisible(current is not None)
        self._empty.setVisible(current is None)
        if current is None:
            return
        deck_id = current.data(_ID_ROLE)
        row = next((r for r in self._vm.rows() if r.deck.id == deck_id), None)
        if row is None:
            return
        self._name.setText(row.deck.name)
        self._new_per_day.setValue(row.deck.new_per_day)
        self._reviews_per_day.setValue(row.deck.reviews_per_day)
        self._make_current.setEnabled(not row.is_current)
        self._delete.setEnabled(self._vm.can_delete())

    # -- actions ------------------------------------------------

    def _create_deck(self) -> None:
        name, ok = QInputDialog.getText(self, "New deck", "Deck name:")
        if ok and name.strip():
            self._vm.create(name)

    def _save_editor(self) -> None:
        deck_id = self._current_deck_id()
        if deck_id is not None:
            self._vm.save(
                deck_id,
                name=self._name.text(),
                new_per_day=self._new_per_day.value(),
                reviews_per_day=self._reviews_per_day.value(),
            )

    def _make_current_deck(self) -> None:
        deck_id = self._current_deck_id()
        if deck_id is not None:
            self._vm.make_current(deck_id)

    def _delete_deck(self) -> None:
        deck_id = self._current_deck_id()
        if deck_id is not None:
            self._vm.delete(deck_id)

    def _current_deck_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        deck_id = item.data(_ID_ROLE)
        return int(deck_id) if deck_id is not None else None
