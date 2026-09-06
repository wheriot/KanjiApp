"""The Settings screen: app-wide theme and scheduling preferences."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kanji_app.services.settings import REVIEW_INPUTS, THEMES
from kanji_app.ui.view_models.settings_vm import SettingsViewModel
from kanji_app.ui.views.credits import CreditsDialog

_THEME_LABELS = {"system": "Follow system", "light": "Light", "dark": "Dark"}
_INPUT_LABELS = {
    "reveal": "Flip and self-grade",
    "choose": "Pick from four options",
    "type": "Type the reading",
}


class SettingsView(QWidget):
    def __init__(self, vm: SettingsViewModel) -> None:
        super().__init__()
        self._vm = vm

        self._theme = QComboBox()
        for key in THEMES:
            self._theme.addItem(_THEME_LABELS[key], key)
        self._theme.setCurrentIndex(self._theme.findData(vm.theme))
        self._theme.currentIndexChanged.connect(
            lambda: self._vm.set_theme(self._theme.currentData())
        )

        self._retention = QDoubleSpinBox()
        self._retention.setRange(0.80, 0.97)
        self._retention.setSingleStep(0.01)
        self._retention.setDecimals(2)
        self._retention.setValue(vm.fsrs_retention)
        self._retention.valueChanged.connect(self._vm.set_retention)

        self._review_input = QComboBox()
        for key in REVIEW_INPUTS:
            self._review_input.addItem(_INPUT_LABELS[key], key)
        self._review_input.setCurrentIndex(self._review_input.findData(vm.review_input))
        self._review_input.currentIndexChanged.connect(
            lambda: self._vm.set_review_input(self._review_input.currentData())
        )

        appearance = QGroupBox("Appearance and scheduling")
        form = QFormLayout(appearance)
        form.addRow("Theme", self._theme)
        form.addRow("Target retention", self._retention)
        form.addRow("", _hint("Higher retention = more reviews, shorter intervals."))
        form.addRow("Review answers", self._review_input)

        self._credits = QPushButton("Credits and licences…")
        self._credits.clicked.connect(self._open_credits)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(appearance)
        layout.addWidget(self._credits, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)

    def _open_credits(self) -> None:
        CreditsDialog(self).exec()


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setEnabled(False)
    label.setWordWrap(True)
    return label
