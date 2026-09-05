"""The application's main window.

Phase 0: a placeholder shell with the navigation skeleton. Real screens are
added from Phase 2 onward.
"""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from kanji_app import __version__

SCREENS = ("Dashboard", "Review", "Browse", "Stats", "Settings")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kanji App")
        self.resize(960, 640)

        self._stack = QStackedWidget()
        for name in SCREENS:
            self._stack.addWidget(_placeholder(name))
        self.setCentralWidget(self._stack)

        nav = self.addToolBar("Navigation")
        nav.setMovable(False)
        for index, name in enumerate(SCREENS):
            nav.addAction(name, partial(self._stack.setCurrentIndex, index))

        self.statusBar().showMessage(f"Kanji App v{__version__} — Phase 0 skeleton")

    def current_screen_name(self) -> str:
        return SCREENS[self._stack.currentIndex()]


def _placeholder(name: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title = QLabel(name)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    font = title.font()
    font.setPointSize(24)
    title.setFont(font)
    layout.addWidget(title)
    layout.addWidget(
        QLabel("Not built yet — see PLAN.md for the roadmap."),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    return widget
