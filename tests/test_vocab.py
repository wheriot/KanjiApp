from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from kanji_app.core.models import CardMode, Rating
from kanji_app.data.repositories import VocabRepo
from kanji_app.services.catalog import KanjiCatalog
from kanji_app.services.study import StudyService

NOON = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def vocab_db(kanji_db: sqlite3.Connection) -> sqlite3.Connection:
    kanji_db.executescript(
        """
        INSERT INTO vocab (id, expression, kana, jlpt, grade) VALUES
            (1, '水', 'みず', 5, 1),
            (2, '山川', 'やまかわ', 5, 2),
            (3, '一人', 'ひとり', 5, 1);
        INSERT INTO vocab_gloss (vocab_id, value) VALUES
            (1, 'water'),
            (2, 'mountains and rivers'),
            (3, 'one person'), (3, 'alone');
        INSERT INTO vocab_kanji (vocab_id, kanji_id) VALUES
            (1, 1), (2, 1), (2, 2), (3, 3);
        """
    )
    return kanji_db


def test_vocab_repo_find_and_hydrate(vocab_db: sqlite3.Connection) -> None:
    repo = VocabRepo(vocab_db)
    assert repo.count() == 3

    hitori = repo.find(text="alone")[0]
    assert hitori.expression == "一人"
    assert hitori.glosses == ("one person", "alone")
    assert 3 in hitori.kanji_ids

    assert [v.expression for v in repo.find(text="やまかわ")] == ["山川"]


def test_vocab_repo_filters_by_jlpt_and_grade(vocab_db: sqlite3.Connection) -> None:
    repo = VocabRepo(vocab_db)
    assert {v.expression for v in repo.find(grade=1)} == {"水", "一人"}
    assert [v.expression for v in repo.find(grade=2)] == ["山川"]
    assert [v.expression for v in repo.find(jlpt=5, grade=2)] == ["山川"]
    assert repo.distinct_values("grade") == [1, 2]
    assert repo.distinct_values("jlpt") == [5]


def test_vocab_carries_grade(vocab_db: sqlite3.Connection) -> None:
    (word,) = VocabRepo(vocab_db).find(text="山川")
    assert word.grade == 2
    assert word.jlpt == 5


def test_vocab_for_kanji(vocab_db: sqlite3.Connection) -> None:
    repo = VocabRepo(vocab_db)
    words = {v.expression for v in repo.for_kanji(1)}  # kanji 水
    assert words == {"水", "山川"}


def test_catalog_exposes_vocab(vocab_db: sqlite3.Connection) -> None:
    catalog = KanjiCatalog(vocab_db)
    assert catalog.vocab_total() == 3
    entry = catalog.get_vocab(2)
    assert entry is not None and entry.expression == "山川"
    assert [v.expression for v in catalog.vocab_for_kanji(2)] == ["山川"]


def test_study_service_adds_vocab_cards(study_service: StudyService) -> None:
    """Uses the shipped kanji.db, which has real vocab."""
    deck = study_service.default_deck()
    added = study_service.add_vocab(deck.id, 1, NOON)
    assert added == 2
    assert study_service.add_vocab(deck.id, 1, NOON) == 0
    assert study_service.is_vocab_in_deck(deck.id, 1)

    modes = {item.card.mode for item in study_service.start_session(deck.id, NOON)}
    assert modes == {CardMode.RECOGNITION, CardMode.RECALL}


def test_vocab_review_item_faces(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    study_service.add_vocab(deck.id, 1, NOON)
    items = study_service.start_session(deck.id, NOON)

    recognition = next(i for i in items if i.card.mode == CardMode.RECOGNITION)
    recall = next(i for i in items if i.card.mode == CardMode.RECALL)

    # recognition shows the word, reveals the meaning; recall is the mirror
    assert recognition.prompt == recall.answer
    assert recognition.answer == recall.prompt
    assert recognition.answer_note == recall.answer_note  # the kana, shown on reveal either way

    study_service.answer(recognition.card, Rating.GOOD, NOON)  # persists without error
