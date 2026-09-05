"""The Review screen: run through a deck's due queue with FSRS grading."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from kanji_app.core.models import Rating
from kanji_app.ui.view_models.review_vm import ReviewViewModel
from kanji_app.ui.widgets.card_widget import CardFace

_RATING_KEYS = {
    Rating.AGAIN: "1",
    Rating.HARD: "2",
    Rating.GOOD: "3",
    Rating.EASY: "4",
}


class ReviewView(QWidget):
    def __init__(self, vm: ReviewViewModel) -> None:
        super().__init__()
        self._vm = vm

        self._status = QLabel()
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._card = CardFace()

        # footer: page 0 = idle/summary, page 1 = "show answer", page 2 = ratings
        self._footer = QStackedWidget()
        self._footer.addWidget(self._build_idle_page())
        self._footer.addWidget(self._build_reveal_page())
        self._footer.addWidget(self._build_rating_page())

        layout = QVBoxLayout(self)
        layout.addWidget(self._status)
        layout.addWidget(self._card, stretch=1)
        layout.addWidget(self._footer)

        self._install_shortcuts()
        self._vm.state_changed.connect(self._render)
        self._render()

    # -- pages ------------------------------------------------------

    def _build_idle_page(self) -> QWidget:
        page = QWidget()
        box = QVBoxLayout(page)
        self._idle_label = QLabel()
        self._idle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._start_button = QPushButton("Start studying")
        self._start_button.clicked.connect(self._vm.start)
        box.addWidget(self._idle_label)
        box.addWidget(self._start_button)
        return page

    def _build_reveal_page(self) -> QWidget:
        page = QWidget()
        box = QHBoxLayout(page)
        button = QPushButton("Show answer  (Space)")
        button.clicked.connect(self._vm.reveal)
        box.addWidget(button)
        return page

    def _build_rating_page(self) -> QWidget:
        page = QWidget()
        box = QHBoxLayout(page)
        for rating, key in _RATING_KEYS.items():
            button = QPushButton(f"{rating.name.title()}  ({key})")
            button.clicked.connect(lambda _=False, r=rating: self._vm.answer(r))
            box.addWidget(button)
        return page

    # -- keyboard -------------------------------------------------

    def _install_shortcuts(self) -> None:
        reveal = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        reveal.activated.connect(self._on_space)
        for rating, key in _RATING_KEYS.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda r=rating: self._on_rating_key(r))

    def _on_space(self) -> None:
        if self._vm.in_progress and not self._vm.revealed:
            self._vm.reveal()

    def _on_rating_key(self, rating: Rating) -> None:
        if self._vm.in_progress and self._vm.revealed:
            self._vm.answer(rating)

    # -- rendering -----------------------------------------------

    def refresh(self) -> None:
        """Re-read pending counts (e.g. after kanji were added on the Browse tab)."""
        if not self._vm.in_progress:
            self._render()

    def _render(self) -> None:
        item = self._vm.current
        self._card.show_item(item, self._vm.revealed)

        if item is None:
            self._footer.setCurrentIndex(0)
            self._render_idle()
            return

        self._status.setText(f"{self._vm.answered} done  ·  {self._vm.remaining} left")
        self._footer.setCurrentIndex(2 if self._vm.revealed else 1)

    def _render_idle(self) -> None:
        pending = self._vm.pending_counts()
        if self._vm.answered > 0 and pending.total == 0:
            self._status.setText("Session complete")
            self._idle_label.setText(f"All done — {self._vm.answered} cards reviewed. 🎉")
            self._start_button.setVisible(False)
            return

        self._status.setText("Review")
        self._start_button.setVisible(pending.total > 0)
        if pending.total == 0:
            self._idle_label.setText(
                "Nothing due right now.\nAdd kanji from the Browse tab to build your deck."
            )
        else:
            self._idle_label.setText(
                f"{pending.due} review{_s(pending.due)} and "
                f"{pending.new} new card{_s(pending.new)} waiting."
            )


def _s(n: int) -> str:
    return "" if n == 1 else "s"
