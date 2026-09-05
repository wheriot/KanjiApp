"""View-model for the Review screen.

Owns the in-progress session: the queue, the cursor, and whether the answer is
currently revealed. Talks to :class:`StudyService`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import QObject, Signal

from kanji_app.core.models import Rating
from kanji_app.core.review_session import DeckCounts
from kanji_app.services.study import ReviewItem, StudyService


class ReviewViewModel(QObject):
    state_changed = Signal()  # queue, cursor, or reveal state changed

    def __init__(self, study: StudyService, deck_id: int) -> None:
        super().__init__()
        self._study = study
        self._deck_id = deck_id
        self._queue: list[ReviewItem] = []
        self._cursor = 0
        self._revealed = False
        self._answered = 0

    # -- state ------------------------------------------------------

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

    def pending_counts(self) -> DeckCounts:
        return self._study.deck_counts(self._deck_id)

    # -- commands -------------------------------------------------

    def start(self, now: datetime | None = None) -> None:
        self._queue = self._study.start_session(self._deck_id, now)
        self._cursor = 0
        self._revealed = False
        self._answered = 0
        self.state_changed.emit()

    def reveal(self) -> None:
        if self.current is not None and not self._revealed:
            self._revealed = True
            self.state_changed.emit()

    def answer(self, rating: Rating, now: datetime | None = None) -> None:
        item = self.current
        if item is None or not self._revealed:
            return
        self._study.answer(item.card, rating, now or datetime.now(UTC))
        self._cursor += 1
        self._answered += 1
        self._revealed = False
        self.state_changed.emit()
