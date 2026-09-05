"""Light/dark theme handling and application-font loading."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from kanji_app.config import FONTS_DIR

_SCHEMES = {
    "system": Qt.ColorScheme.Unknown,
    "light": Qt.ColorScheme.Light,
    "dark": Qt.ColorScheme.Dark,
}

# Families we prefer for Japanese text, best first. The bundled Noto face wins
# when present; otherwise Qt falls through to whatever the OS provides.
_JP_FALLBACKS = ("Noto Sans JP", "Noto Sans CJK JP", "Yu Gothic UI", "Meiryo", "Hiragino Sans")


def apply_theme(app: QApplication, theme: str) -> None:
    app.styleHints().setColorScheme(_SCHEMES.get(theme, Qt.ColorScheme.Unknown))


def load_fonts(app: QApplication) -> None:
    """Register any bundled fonts and set a Japanese-capable default family."""
    loaded: list[str] = []
    if FONTS_DIR.is_dir():
        for path in sorted(FONTS_DIR.glob("*.[to]tf")):
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id != -1:
                loaded += QFontDatabase.applicationFontFamilies(font_id)

    available = set(QFontDatabase.families())
    preferred = [fam for fam in (*loaded, *_JP_FALLBACKS) if fam in available]
    if preferred:
        base = app.font()
        font = QFont(preferred[0], base.pointSize() or 10)
        font.setFamilies(preferred)
        app.setFont(font)
