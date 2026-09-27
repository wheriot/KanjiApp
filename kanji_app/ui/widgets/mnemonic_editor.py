"""A small note editor for the learner's own mnemonic, with an explicit Save."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget


class MnemonicEditor(QWidget):
    saved = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._baseline = ""

        self._edit = QPlainTextEdit()
        self._edit.setPlaceholderText("Write your own memory aid: a story, image, or sound-alike")
        self._edit.setFixedHeight(72)
        self._edit.textChanged.connect(self._update_save)

        self._save = QPushButton("Save mnemonic")
        self._save.clicked.connect(self._emit_saved)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._save)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit)
        layout.addLayout(buttons)
        self._update_save()

    def set_text(self, text: str) -> None:
        self._baseline = text
        self._edit.setPlainText(text)
        self._update_save()

    def set_editable(self, editable: bool) -> None:
        self._edit.setEnabled(editable)
        self._update_save()

    def _emit_saved(self) -> None:
        text = self._edit.toPlainText().strip()
        self._baseline = text
        self._update_save()
        self.saved.emit(text)

    def _update_save(self) -> None:
        changed = self._edit.toPlainText().strip() != self._baseline.strip()
        self._save.setEnabled(self._edit.isEnabled() and changed)
