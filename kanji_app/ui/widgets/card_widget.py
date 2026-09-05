"""The flashcard face shown during review.

The service has already rendered each :class:`ReviewItem` to plain text
(``prompt`` / ``prompt_note`` always visible, ``answer`` / ``answer_note`` on
reveal), so this widget just lays the pieces out — it knows nothing about card
modes or subject types.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from kanji_app.services.study import ReviewItem
from kanji_app.ui.widgets.stroke_order_widget import StrokeOrderWidget


class CardFace(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._prompt = _text(28)
        self._prompt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._prompt_note = _text(16, faint=True)
        self._divider = QLabel()
        self._divider.setFixedHeight(1)
        self._divider.setStyleSheet("background: palette(mid);")
        self._answer = _text(24)
        self._answer_note = _text(15, faint=True)
        self._stroke = StrokeOrderWidget()

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self._prompt)
        layout.addWidget(self._prompt_note)
        layout.addWidget(self._divider)
        layout.addWidget(self._answer)
        layout.addWidget(self._answer_note)
        layout.addWidget(self._stroke, stretch=1)
        layout.addStretch(1)

    def show_item(self, item: ReviewItem | None, revealed: bool) -> None:
        if item is None:
            for label in (self._prompt, self._prompt_note, self._answer, self._answer_note):
                label.clear()
            self._stroke.set_drawing(None)
            self._set_answer_visible(False)
            return

        self._prompt.setText(item.prompt)
        self._prompt_note.setText(item.prompt_note)
        self._prompt_note.setVisible(bool(item.prompt_note))

        self._answer.setText(item.answer)
        self._answer_note.setText(item.answer_note)
        self._stroke.set_drawing(item.stroke if revealed else None)
        self._set_answer_visible(
            revealed, has_note=bool(item.answer_note), has_stroke=item.stroke is not None
        )

    def _set_answer_visible(
        self, revealed: bool, *, has_note: bool = False, has_stroke: bool = False
    ) -> None:
        self._divider.setVisible(revealed)
        self._answer.setVisible(revealed)
        self._answer_note.setVisible(revealed and has_note)
        self._stroke.setVisible(revealed and has_stroke)


def _text(point_size: int, *, faint: bool = False) -> QLabel:
    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    font = label.font()
    font.setPointSize(point_size)
    label.setFont(font)
    if faint:
        label.setEnabled(False)
    return label
