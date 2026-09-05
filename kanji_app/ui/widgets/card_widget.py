"""The flashcard face shown during review.

Renders one :class:`ReviewItem` in either its question or its revealed state,
for both card modes:

- ``RECOGNITION`` — the kanji is always shown; revealing adds meaning + readings
- ``RECALL`` — meaning + readings are the prompt; revealing adds the kanji
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from kanji_app.core.models import CardMode, Kanji, ReadingType
from kanji_app.services.study import ReviewItem

_HIDDEN_LITERAL = "?"


class CardFace(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._literal = QLabel()
        self._literal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        literal_font = self._literal.font()
        literal_font.setPointSize(96)
        self._literal.setFont(literal_font)
        self._literal.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._prompt = QLabel()  # shown instead of the kanji for a hidden recall card
        self._prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prompt_font = self._prompt.font()
        prompt_font.setPointSize(20)
        self._prompt.setFont(prompt_font)
        self._prompt.setWordWrap(True)

        self._meaning = QLabel()
        self._meaning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meaning_font = self._meaning.font()
        meaning_font.setPointSize(16)
        self._meaning.setFont(meaning_font)
        self._meaning.setWordWrap(True)

        self._readings = QLabel()
        self._readings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._readings.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self._literal)
        layout.addWidget(self._prompt)
        layout.addWidget(self._meaning)
        layout.addWidget(self._readings)
        layout.addStretch(1)

    def show_item(self, item: ReviewItem | None, revealed: bool) -> None:
        if item is None:
            for label in (self._literal, self._prompt, self._meaning, self._readings):
                label.clear()
            return

        kanji = item.kanji
        meanings = ", ".join(m.value for m in kanji.meanings)
        readings = _format_readings(kanji)
        is_recall = item.card.mode == CardMode.RECALL

        show_kanji = not is_recall or revealed
        self._literal.setText(kanji.literal if show_kanji else "")
        self._literal.setVisible(show_kanji)
        self._prompt.setText(_HIDDEN_LITERAL if is_recall and not revealed else "")
        self._prompt.setVisible(is_recall and not revealed)

        if is_recall:
            # meaning + readings are the always-visible prompt for a recall card
            self._meaning.setText(meanings)
            self._readings.setText(readings)
            self._meaning.setVisible(True)
            self._readings.setVisible(bool(readings))
        else:
            self._meaning.setText(meanings)
            self._readings.setText(readings)
            self._meaning.setVisible(revealed)
            self._readings.setVisible(revealed and bool(readings))


def _format_readings(kanji: Kanji) -> str:
    on = "、".join(kanji.readings_of(ReadingType.ON))
    kun = "、".join(kanji.readings_of(ReadingType.KUN))
    parts = [p for p in (on, kun) if p]
    return "  /  ".join(parts)
