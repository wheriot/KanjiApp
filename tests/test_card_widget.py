from __future__ import annotations

from datetime import UTC, datetime

from kanji_app.core.models import (
    Card,
    CardMode,
    CardState,
    SchedulingState,
    SubjectType,
)
from kanji_app.services.study import ReviewItem
from kanji_app.ui.app import build_app
from kanji_app.ui.widgets.card_widget import CardFace


def _card(mode: CardMode, subject_type: SubjectType = SubjectType.KANJI) -> Card:
    return Card(
        id=1,
        deck_id=1,
        subject_type=subject_type,
        subject_id=1,
        mode=mode,
        scheduling=SchedulingState(CardState.NEW, 0, datetime.now(UTC), None, None, 0, 0),
    )


def test_prompt_always_visible_answer_hidden_until_reveal() -> None:
    build_app([])
    face = CardFace()
    item = ReviewItem(
        card=_card(CardMode.RECOGNITION),
        prompt="水",
        prompt_note="",
        answer="water",
        answer_note="スイ / みず",
    )

    face.show_item(item, revealed=False)
    assert face._prompt.text() == "水"
    assert face._answer.isHidden()

    face.show_item(item, revealed=True)
    assert face._answer.text() == "water"
    assert not face._answer.isHidden()
    assert not face._answer_note.isHidden()


def test_vocab_recall_shows_meaning_then_word() -> None:
    build_app([])
    face = CardFace()
    item = ReviewItem(
        card=_card(CardMode.RECALL, SubjectType.VOCAB),
        prompt="one person; he",
        prompt_note="",
        answer="一人",
        answer_note="ひとり",
    )

    face.show_item(item, revealed=False)
    assert face._prompt.text() == "one person; he"
    assert face._answer.isHidden()

    face.show_item(item, revealed=True)
    assert face._answer.text() == "一人"
    assert face._answer_note.text() == "ひとり"


def test_none_clears_face() -> None:
    build_app([])
    face = CardFace()
    face.show_item(None, revealed=False)
    assert face._prompt.text() == ""
    assert face._answer.isHidden()
