"""The Review screen: run through a deck's due queue.

Supports three answer styles (chosen in Settings): flip-and-self-grade, pick
from four options, or type the reading. The footer is a stack of small panels
switched by ``(input_mode, phase)``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from kanji_app.core.models import Rating
from kanji_app.ui.view_models.review_vm import ReviewViewModel
from kanji_app.ui.widgets.card_widget import CardFace

_RATING_KEYS = {Rating.AGAIN: "1", Rating.HARD: "2", Rating.GOOD: "3", Rating.EASY: "4"}
_IDLE, _REVEAL_Q, _REVEAL_A, _CHOOSE_Q, _TYPE_Q, _CONTINUE = range(6)


class ReviewView(QWidget):
    def __init__(self, vm: ReviewViewModel) -> None:
        super().__init__()
        self._vm = vm

        self._status = QLabel()
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._card = CardFace()

        self._footer = QStackedWidget()
        self._footer.addWidget(self._build_idle_page())
        self._footer.addWidget(self._build_reveal_page())
        self._footer.addWidget(self._build_rating_page())
        self._footer.addWidget(self._build_choose_page())
        self._footer.addWidget(self._build_type_page())
        self._footer.addWidget(self._build_continue_page())

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

    def _build_choose_page(self) -> QWidget:
        page = QWidget()
        box = QHBoxLayout(page)
        self._choice_buttons: list[QPushButton] = []
        for index in range(4):
            button = QPushButton()
            button.clicked.connect(lambda _=False, i=index: self._vm.choose(i))
            self._choice_buttons.append(button)
            box.addWidget(button)
        return page

    def _build_type_page(self) -> QWidget:
        page = QWidget()
        box = QHBoxLayout(page)
        self._reading_input = QLineEdit()
        self._reading_input.setPlaceholderText("Type the reading (kana or romaji), then Enter")
        self._reading_input.returnPressed.connect(self._submit_reading)
        submit = QPushButton("Submit")
        submit.clicked.connect(self._submit_reading)
        box.addWidget(self._reading_input, stretch=1)
        box.addWidget(submit)
        return page

    def _build_continue_page(self) -> QWidget:
        page = QWidget()
        box = QHBoxLayout(page)
        button = QPushButton("Continue  (Space)")
        button.clicked.connect(self._vm.continue_)
        box.addWidget(button)
        return page

    # -- keyboard -------------------------------------------------

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._on_space)
        QShortcut(QKeySequence(Qt.Key.Key_Return), self, self._on_space)
        for rating, key in _RATING_KEYS.items():
            QShortcut(QKeySequence(key), self, lambda r=rating: self._on_number(int(r.value)))

    def _on_space(self) -> None:
        page = self._footer.currentIndex()
        if page == _REVEAL_Q:
            self._vm.reveal()
        elif page == _CONTINUE:
            self._vm.continue_()

    def _on_number(self, n: int) -> None:
        page = self._footer.currentIndex()
        if page == _REVEAL_A:
            self._vm.answer(Rating(n))
        elif page == _CHOOSE_Q:
            options = self._vm.current.options if self._vm.current else ()
            if 1 <= n <= len(options):
                self._vm.choose(n - 1)

    def _submit_reading(self) -> None:
        self._vm.submit_reading(self._reading_input.text())

    # -- rendering -----------------------------------------------

    def start_session(self) -> None:
        self._vm.start()

    def refresh(self) -> None:
        if not self._vm.in_progress:
            self._render()

    def _render(self) -> None:
        item = self._vm.current
        self._card.show_item(item, self._vm.revealed)

        if item is None:
            self._footer.setCurrentIndex(_IDLE)
            self._render_idle()
            return

        left = f"{self._vm.answered} done  ·  {self._vm.remaining} left"
        if self._vm.revealed and self._vm.graded_correct is not None:
            mark = "Correct" if self._vm.graded_correct else "Not quite"
            self._status.setText(f"{mark}   —   {left}")
        else:
            self._status.setText(left)

        self._footer.setCurrentIndex(self._page_for())

    def _page_for(self) -> int:
        if self._vm.revealed:
            return _REVEAL_A if self._vm.input_mode == "reveal" else _CONTINUE
        if self._vm.input_mode == "choose":
            options = self._vm.current.options if self._vm.current else ()
            for i, button in enumerate(self._choice_buttons):
                button.setText(options[i] if i < len(options) else "")
                button.setVisible(bool(button.text()))
            return _CHOOSE_Q
        if self._vm.input_mode == "type":
            self._reading_input.clear()
            self._reading_input.setFocus()
            return _TYPE_Q
        return _REVEAL_Q

    def _render_idle(self) -> None:
        summary = self._vm.today_summary()
        self._status.setText("Review")

        if summary.waiting > 0:
            self._start_button.setVisible(True)
            self._idle_label.setText(
                f"{summary.due} review{_s(summary.due)} and "
                f"{summary.new_available} new card{_s(summary.new_available)} ready."
            )
            return

        self._start_button.setVisible(False)

        if summary.limit_reached:
            held = []
            if summary.capped_new:
                held.append(f"{summary.capped_new} new")
            if summary.capped_due:
                held.append(f"{summary.capped_due} due")
            self._idle_label.setText(
                f"Daily limit reached — {summary.reviewed_today} "
                f"card{_s(summary.reviewed_today)} studied today.\n"
                f"{' and '.join(held)} held back for tomorrow. "
                "Raise the limit on the Decks screen to keep going."
            )
        elif self._vm.answered > 0:
            self._status.setText("Session complete")
            self._idle_label.setText(f"All done — {self._vm.answered} cards reviewed. 🎉")
        elif summary.next_due is not None:
            self._idle_label.setText(f"All caught up. Next review {_relative(summary.next_due)}.")
        else:
            self._idle_label.setText(
                "Nothing due yet.\nAdd kanji or vocab from the Browse tab to build your deck."
            )


def _s(n: int) -> str:
    return "" if n == 1 else "s"


def _relative(when: datetime) -> str:
    seconds = (when - datetime.now(UTC)).total_seconds()
    if seconds <= 90:
        return "in a moment"
    minutes = seconds / 60
    if minutes < 90:
        return f"in about {round(minutes)} minutes"
    hours = minutes / 60
    if hours < 36:
        return f"in about {round(hours)} hours"
    return f"in about {round(hours / 24)} days"
