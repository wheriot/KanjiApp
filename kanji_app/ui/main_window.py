"""The application's main window: a stacked set of screens with a nav toolbar.

Screens are added phase by phase. Anything not built yet shows a placeholder.
"""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from kanji_app import __version__
from kanji_app.services.catalog import KanjiCatalog
from kanji_app.services.study import StudyService
from kanji_app.ui.theme import apply_theme
from kanji_app.ui.view_models.catalog_vm import CatalogViewModel
from kanji_app.ui.view_models.dashboard_vm import DashboardViewModel
from kanji_app.ui.view_models.review_vm import ReviewViewModel
from kanji_app.ui.view_models.settings_vm import SettingsViewModel
from kanji_app.ui.view_models.stats_vm import StatsViewModel
from kanji_app.ui.views.browser_view import BrowserView
from kanji_app.ui.views.dashboard_view import DashboardView
from kanji_app.ui.views.review_view import ReviewView
from kanji_app.ui.views.settings_view import SettingsView
from kanji_app.ui.views.stats_view import StatsView

SCREENS = ("Dashboard", "Review", "Browse", "Stats", "Settings")


class MainWindow(QMainWindow):
    def __init__(
        self,
        catalog: KanjiCatalog | None = None,
        study: StudyService | None = None,
    ) -> None:
        super().__init__()
        self._catalog = catalog
        self._study = study
        self._deck_id = study.default_deck().id if study is not None else None
        self._stats = study.stats_service() if study is not None else None

        self._dashboard: DashboardView | None = None
        self._review: ReviewView | None = None
        self._stats_view: StatsView | None = None
        self._settings_vm: SettingsViewModel | None = None
        self._catalog_vm: CatalogViewModel | None = None

        self.setWindowTitle("Kanji App")
        self.resize(1000, 680)

        self._stack = QStackedWidget()
        self._screens: dict[str, QWidget] = {name: self._build_screen(name) for name in SCREENS}
        for name in SCREENS:
            self._stack.addWidget(self._screens[name])
        self.setCentralWidget(self._stack)

        nav = self.addToolBar("Navigation")
        nav.setMovable(False)
        for index, name in enumerate(SCREENS):
            nav.addAction(name, partial(self._stack.setCurrentIndex, index))
            QShortcut(
                QKeySequence(f"Ctrl+{index + 1}"),
                self,
                partial(self._stack.setCurrentIndex, index),
            )

        self._wire()
        self.statusBar().showMessage(f"Kanji App v{__version__}")
        self._stack.currentChanged.connect(self._on_screen_changed)
        self._go_to("Dashboard" if study is not None else "Browse")

    def current_screen_name(self) -> str:
        return SCREENS[self._stack.currentIndex()]

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._catalog is not None:
            self._catalog.close()
        if self._study is not None:
            self._study.close()
        super().closeEvent(event)

    # -- construction --------------------------------------------------

    def _build_screen(self, name: str) -> QWidget:
        if name == "Dashboard" and self._study is not None and self._deck_id is not None:
            assert self._stats is not None
            self._dashboard = DashboardView(
                DashboardViewModel(self._study, self._stats, self._deck_id)
            )
            return self._dashboard
        if name == "Review" and self._study is not None and self._deck_id is not None:
            self._review = ReviewView(ReviewViewModel(self._study, self._deck_id))
            return self._review
        if name == "Browse" and self._catalog is not None:
            self._catalog_vm = CatalogViewModel(self._catalog, self._study, self._deck_id)
            return BrowserView(self._catalog_vm)
        if name == "Stats" and self._stats is not None and self._deck_id is not None:
            self._stats_view = StatsView(StatsViewModel(self._stats, self._deck_id))
            return self._stats_view
        if name == "Settings" and self._study is not None and self._deck_id is not None:
            self._settings_vm = SettingsViewModel(self._study, self._deck_id)
            return SettingsView(self._settings_vm)
        return _placeholder(name)

    def _wire(self) -> None:
        if self._dashboard is not None:
            self._dashboard.study_requested.connect(self._start_studying)
        if self._catalog_vm is not None:
            self._catalog_vm.deck_changed.connect(self._refresh_study_screens)
        if self._settings_vm is not None:
            self._settings_vm.theme_changed.connect(self._apply_theme)
            self._settings_vm.changed.connect(self._refresh_study_screens)

    def _apply_theme(self, theme: str) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, theme)

    # -- behaviour ---------------------------------------------------

    def _start_studying(self) -> None:
        self._go_to("Review")
        if self._review is not None:
            self._review.start_session()

    def _refresh_study_screens(self) -> None:
        for screen in (self._dashboard, self._review, self._stats_view):
            if screen is not None:
                screen.refresh()

    def _on_screen_changed(self, _index: int) -> None:
        screen = self._stack.currentWidget()
        for known in (self._dashboard, self._review, self._stats_view):
            if screen is known and known is not None:
                known.refresh()

    def _go_to(self, name: str) -> None:
        self._stack.setCurrentIndex(SCREENS.index(name))


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
