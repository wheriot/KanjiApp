"""Shared "Add all filtered results to the deck" button + confirmation flow."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMessageBox, QPushButton


class AddAllButton(QPushButton):
    """A button that confirms, then bulk-adds the current results to the deck.

    ``pending`` returns how many results are not in the deck yet; ``add`` performs
    the add and returns how many were added.
    """

    def __init__(
        self,
        noun: str,
        *,
        pending: Callable[[], int],
        add: Callable[[], int],
        can_add: Callable[[], bool],
    ) -> None:
        super().__init__("Add all…")
        self._noun = noun
        self._pending = pending
        self._add = add
        self._can_add = can_add
        self.clicked.connect(self._run)

    def refresh(self) -> None:
        count = self._pending() if self._can_add() else 0
        self.setVisible(self._can_add())
        self.setEnabled(count > 0)
        self.setText("All in deck" if self._can_add() and count == 0 else "Add all…")

    def _run(self) -> None:
        count = self._pending()
        if count == 0:
            return
        confirm = QMessageBox.question(
            self,
            "Add to deck",
            f"Add {count} {self._noun} ({count * 2} cards) to your current deck?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        added = self._add()
        QMessageBox.information(self, "Added", f"Added {added} {self._noun} to your deck.")
