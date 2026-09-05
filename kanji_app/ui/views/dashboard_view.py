"""The Dashboard screen: today's workload and a jump into studying."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kanji_app.ui.view_models.dashboard_vm import DashboardViewModel


class DashboardView(QWidget):
    study_requested = Signal()

    def __init__(self, vm: DashboardViewModel) -> None:
        super().__init__()
        self._vm = vm

        self._title = QLabel()
        title_font = self._title.font()
        title_font.setPointSize(20)
        self._title.setFont(title_font)

        self._due = _StatTile("Due")
        self._new = _StatTile("New today")
        self._reviewed = _StatTile("Reviewed today")
        self._streak = _StatTile("Day streak")
        tiles = QHBoxLayout()
        for tile in (self._due, self._new, self._reviewed, self._streak):
            tiles.addWidget(tile)

        self._start = QPushButton()
        self._start.clicked.connect(self.study_requested)
        self._start.setMinimumHeight(40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        layout.addWidget(self._title)
        layout.addLayout(tiles)
        layout.addWidget(self._start)
        layout.addStretch(1)

        self._vm.changed.connect(self._render)
        self._render()

    def refresh(self) -> None:
        self._vm.refresh()

    def _render(self) -> None:
        self._title.setText(self._vm.deck_name)
        self._due.set_value(self._vm.due)
        self._new.set_value(self._vm.new_available)
        self._reviewed.set_value(self._vm.reviewed_today)
        self._streak.set_value(self._vm.streak_days)

        self._start.setEnabled(self._vm.has_work)
        self._start.setText(
            "Start studying" if self._vm.has_work else "Nothing due — add kanji from Browse"
        )


class _StatTile(QFrame):
    def __init__(self, caption: str) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._value = QLabel("0")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_font = self._value.font()
        value_font.setPointSize(28)
        value_font.setBold(True)
        self._value.setFont(value_font)

        caption_label = QLabel(caption)
        caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption_label.setEnabled(False)

        box = QVBoxLayout(self)
        box.addWidget(self._value)
        box.addWidget(caption_label)

    def set_value(self, value: int) -> None:
        self._value.setText(str(value))
