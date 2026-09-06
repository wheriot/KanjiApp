"""View-model for the Review screen.

Owns the in-progress session and supports three answer styles (from settings):

- ``reveal`` — flip the card, then self-grade Again/Hard/Good/Easy
- ``choose`` — pick the answer from four options; graded automatically
- ``type``   — type the reading (kana or romaji); graded automatically

For ``choose`` / ``type`` the card is revealed with the result, then a single
"Continue" advances.
"""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import QObject, Signal

from kanji_app.core.models import Rating
from kanji_app.core.review_session import DeckCounts
from kanji_app.core.romaji import to_kana
from kanji_app.services.study import ReviewItem, StudyService


class ReviewViewModel(QObject):
    state_changed = Signal()

    def __init__(self, study: StudyService, deck_id: int) -> None:
        super().__init__()
        self._study = study
        self._deck_id = deck_id
        self._queue: list[ReviewItem] = []
        self._cursor = 0
        self._revealed = False
        self._answered = 0
        self._graded_correct: bool | None = None  # set in choose/type after answering

    # -- state ------------------------------------------------------

    @property
    def input_mode(self) -> str:
        return self._study.settings.review_input

    @property
    def current(self) -> ReviewItem | None:
        return self._queue[self._cursor] if self._cursor < len(self._queue) else None

    @property
    def revealed(self) -> bool:
        return self._revealed

    @property
    def answered(self) -> int:
        return self._answered

    @property
    def remaining(self) -> int:
        return len(self._queue) - self._cursor

    @property
    def in_progress(self) -> bool:
        return self.current is not None

    @property
    def graded_correct(self) -> bool | None:
        return self._graded_correct

    def pending_counts(self) -> DeckCounts:
        return self._study.deck_counts(self._deck_id)

    # -- commands -------------------------------------------------

    def set_deck(self, deck_id: int) -> None:
        self._deck_id = deck_id
        self._reset()

    def start(self, now: datetime | None = None) -> None:
        self._queue = self._study.start_session(self._deck_id, now)
        self._reset(keep_queue=True)

    def reveal(self) -> None:
        """``reveal`` mode: flip the card."""
        if self.current is not None and not self._revealed:
            self._revealed = True
            self.state_changed.emit()

    def answer(self, rating: Rating, now: datetime | None = None) -> None:
        """``reveal`` mode: self-grade and advance."""
        if self.current is None or not self._revealed:
            return
        self._commit(rating, now)

    def choose(self, option_index: int, now: datetime | None = None) -> None:
        """``choose`` mode: submit a picked option; reveals with the result."""
        item = self.current
        if item is None or self._revealed:
            return
        self._grade_and_reveal(option_index == item.correct_option)

    def submit_reading(self, text: str, now: datetime | None = None) -> None:
        """``type`` mode: submit a typed reading; reveals with the result."""
        item = self.current
        if item is None or self._revealed:
            return
        self._grade_and_reveal(_matches_reading(text, item.accepted))

    def continue_(self, now: datetime | None = None) -> None:
        """``choose`` / ``type`` mode: apply the auto-grade and advance."""
        if self.current is None or self._graded_correct is None:
            return
        rating = Rating.GOOD if self._graded_correct else Rating.AGAIN
        self._commit(rating, now)

    # -- internals ----------------------------------------------

    def _grade_and_reveal(self, correct: bool) -> None:
        self._graded_correct = correct
        self._revealed = True
        self.state_changed.emit()

    def _commit(self, rating: Rating, now: datetime | None) -> None:
        item = self.current
        assert item is not None
        self._study.answer(item.card, rating, now or datetime.now(UTC))
        self._cursor += 1
        self._answered += 1
        self._revealed = False
        self._graded_correct = None
        self.state_changed.emit()

    def _reset(self, *, keep_queue: bool = False) -> None:
        if not keep_queue:
            self._queue = []
        self._cursor = 0
        self._revealed = False
        self._answered = 0
        self._graded_correct = None
        self.state_changed.emit()


def _normalise_reading(text: str) -> str:
    folded = to_kana(text.strip())
    out = []
    for ch in folded:
        code = ord(ch)
        out.append(chr(code - 0x60) if 0x30A1 <= code <= 0x30F6 else ch)
    return "".join(c for c in out if c not in "ー・.-")


def _matches_reading(text: str, accepted: tuple[str, ...]) -> bool:
    if not text.strip() or not accepted:
        return False
    guess = _normalise_reading(text)
    return any(guess == _normalise_reading(a) for a in accepted)
