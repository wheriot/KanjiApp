"""The Settings screen: theme, scheduling target, and daily limits."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from kanji_app.services.settings import THEMES
from kanji_app.ui.view_models.settings_vm import SettingsViewModel
from kanji_app.ui.views.credits import CreditsDialog

_THEME_LABELS = {"system": "Follow system", "light": "Light", "dark": "Dark"}


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

        appearance = QGroupBox("Appearance and scheduling")
        appearance_form = QFormLayout(appearance)
        appearance_form.addRow("Theme", self._theme)
        appearance_form.addRow("Target retention", self._retention)
        appearance_form.addRow(
            "",
            _hint("Higher retention = more reviews, shorter intervals."),
        )

        self._new = QSpinBox()
        self._new.setRange(0, 999)
        self._new.setValue(vm.new_per_day)
        self._new.valueChanged.connect(self._vm.set_new_per_day)

        self._reviews = QSpinBox()
        self._reviews.setRange(0, 9999)
        self._reviews.setValue(vm.reviews_per_day)
        self._reviews.valueChanged.connect(self._vm.set_reviews_per_day)

        limits = QGroupBox("Daily limits (current deck)")
        limits_form = QFormLayout(limits)
        limits_form.addRow("New cards per day", self._new)
        limits_form.addRow("Reviews per day", self._reviews)

        self._credits = QPushButton("Credits and licences…")
        self._credits.clicked.connect(self._open_credits)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(appearance)
        layout.addWidget(limits)
        layout.addWidget(self._credits, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)

    def _open_credits(self) -> None:
        CreditsDialog(self).exec()


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setEnabled(False)
    label.setWordWrap(True)
    return label
