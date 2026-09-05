from __future__ import annotations

from datetime import UTC, datetime

from kanji_app.core.models import (
    Card,
    CardMode,
    CardState,
    Kanji,
    Meaning,
    Reading,
    ReadingType,
    SchedulingState,
    SubjectType,
)
from kanji_app.services.study import ReviewItem
from kanji_app.ui.app import build_app
from kanji_app.ui.widgets.card_widget import CardFace

KANJI = Kanji(
    id=1,
    literal="水",
    stroke_count=4,
    meanings=(Meaning("water"),),
    readings=(Reading(ReadingType.ON, "スイ"), Reading(ReadingType.KUN, "みず")),
)


def _item(mode: CardMode) -> ReviewItem:
    card = Card(
        id=1,
        deck_id=1,
        subject_type=SubjectType.KANJI,
        subject_id=1,
        mode=mode,
        scheduling=SchedulingState(CardState.NEW, 0, datetime.now(UTC), None, None, 0, 0),
    )
    return ReviewItem(card=card, kanji=KANJI)


def test_recognition_hides_answer_until_revealed() -> None:
    build_app([])
    face = CardFace()

    face.show_item(_item(CardMode.RECOGNITION), revealed=False)
    assert face._literal.text() == "水"
    assert face._meaning.isHidden()

    face.show_item(_item(CardMode.RECOGNITION), revealed=True)
    assert face._meaning.text() == "water"
    assert not face._meaning.isHidden()


def test_recall_shows_prompt_and_hides_kanji_until_revealed() -> None:
    build_app([])
    face = CardFace()

    face.show_item(_item(CardMode.RECALL), revealed=False)
    assert face._meaning.text() == "water"
    assert face._literal.isHidden()

    face.show_item(_item(CardMode.RECALL), revealed=True)
    assert face._literal.text() == "水"
    assert not face._literal.isHidden()
