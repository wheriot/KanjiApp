from __future__ import annotations

from kanji_app.ui.app import build_app
from kanji_app.ui.main_window import SCREENS, MainWindow


def test_main_window_constructs_and_navigates() -> None:
    build_app([])
    window = MainWindow()
    assert window.current_screen_name() == "Dashboard"

    window._stack.setCurrentIndex(len(SCREENS) - 1)
    assert window.current_screen_name() == "Settings"
