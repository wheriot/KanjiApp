"""QApplication bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from kanji_app.config import Paths
from kanji_app.services.catalog import open_bundled_catalog
from kanji_app.services.study import open_study_service
from kanji_app.ui.main_window import MainWindow
from kanji_app.ui.theme import apply_theme, load_fonts


def build_app(argv: list[str] | None = None) -> QApplication:
    """Create (or reuse) the QApplication. Split out so tests can drive it."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Kanji App")
    load_fonts(app)
    return app


def run(argv: list[str] | None = None) -> int:
    app = build_app(argv)
    _ = Paths.resolve()  # resolved now so path problems surface at startup
    study = open_study_service()
    apply_theme(app, study.settings.theme)
    window = MainWindow(catalog=open_bundled_catalog(), study=study)
    window.show()
    return app.exec()
