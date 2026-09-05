"""The application's main window: a stacked set of screens with a nav toolbar.

Screens are added phase by phase. Anything not built yet shows a placeholder.
"""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from kanji_app import __version__
from kanji_app.services.catalog import KanjiCatalog
from kanji_app.ui.view_models.catalog_vm import CatalogViewModel
from kanji_app.ui.views.browser_view import BrowserView

SCREENS = ("Dashboard", "Review", "Browse", "Stats", "Settings")


class MainWindow(QMainWindow):
    def __init__(self, catalog: KanjiCatalog | None = None) -> None:
        super().__init__()
        self._catalog = catalog
        self.setWindowTitle("Kanji App")
        self.resize(1000, 680)

        self._stack = QStackedWidget()
        for name in SCREENS:
            self._stack.addWidget(self._build_screen(name))
        self.setCentralWidget(self._stack)
        self._stack.setCurrentIndex(SCREENS.index("Browse"))

        nav = self.addToolBar("Navigation")
        nav.setMovable(False)
        for index, name in enumerate(SCREENS):
            nav.addAction(name, partial(self._stack.setCurrentIndex, index))

        self.statusBar().showMessage(f"Kanji App v{__version__}")

    def current_screen_name(self) -> str:
        return SCREENS[self._stack.currentIndex()]

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._catalog is not None:
            self._catalog.close()
        super().closeEvent(event)

    def _build_screen(self, name: str) -> QWidget:
        if name == "Browse" and self._catalog is not None:
            return BrowserView(CatalogViewModel(self._catalog))
        return _placeholder(name)


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
