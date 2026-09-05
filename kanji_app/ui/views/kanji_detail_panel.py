"""Right-hand panel: everything known about the selected kanji."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from kanji_app.core.kanjivg import StrokeDrawing
from kanji_app.core.models import Kanji, ReadingType
from kanji_app.ui.widgets.stroke_order_widget import StrokeOrderWidget

_PLACEHOLDER = "Select a kanji to see its details."


class KanjiDetailPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._literal = QLabel()
        literal_font = self._literal.font()
        literal_font.setPointSize(64)
        self._literal.setFont(literal_font)
        self._literal.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._meanings = QLabel()
        self._meanings.setWordWrap(True)
        meaning_font = self._meanings.font()
        meaning_font.setPointSize(12)
        self._meanings.setFont(meaning_font)

        self._on = QLabel()
        self._kun = QLabel()
        self._meta = QLabel()
        for label in (self._on, self._kun, self._meta):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("On", self._on)
        form.addRow("Kun", self._kun)
        form.addRow("Info", self._meta)

        self._strokes = StrokeOrderWidget()

        self._placeholder = QLabel(_PLACEHOLDER)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setEnabled(False)

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._literal)
        content_layout.addWidget(self._meanings)
        content_layout.addLayout(form)
        content_layout.addWidget(self._strokes, stretch=1)

        outer = QVBoxLayout(self)
        outer.addWidget(self._placeholder)
        outer.addWidget(self._content)

        self.show_kanji(None, None)

    def show_kanji(self, kanji: Kanji | None, drawing: StrokeDrawing | None) -> None:
        self._placeholder.setVisible(kanji is None)
        self._content.setVisible(kanji is not None)
        self._strokes.set_drawing(drawing)
        if kanji is None:
            return

        self._literal.setText(kanji.literal)
        self._meanings.setText(", ".join(m.value for m in kanji.meanings) or "—")
        self._on.setText("、".join(kanji.readings_of(ReadingType.ON)) or "—")
        self._kun.setText("、".join(kanji.readings_of(ReadingType.KUN)) or "—")
        self._meta.setText(_format_meta(kanji))


def _format_meta(kanji: Kanji) -> str:
    bits = [f"{kanji.stroke_count} strokes"]
    if kanji.jlpt is not None:
        bits.append(f"JLPT N{kanji.jlpt}")
    if kanji.grade is not None:
        bits.append(f"grade {kanji.grade}")
    if kanji.frequency is not None:
        bits.append(f"freq #{kanji.frequency}")
    return " · ".join(bits)
