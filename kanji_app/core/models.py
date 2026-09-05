"""Domain models.

Plain frozen dataclasses and enums. These mirror the database schema
(``kanji_app/data/schema.sql``) but carry no persistence logic — repositories
are responsible for turning rows into these objects and back.

The design is deliberately generic so that vocabulary cards and multiple decks
(planned for later phases) need no structural change:

- a :class:`Card` points at a *subject* via ``(subject_type, subject_id)``
- every card belongs to a :class:`Deck`
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime


class ReadingType(enum.StrEnum):
    ON = "on"
    KUN = "kun"
    NANORI = "nanori"


class SubjectType(enum.StrEnum):
    KANJI = "kanji"
    VOCAB = "vocab"


class CardMode(enum.StrEnum):
    """What the learner is asked to do.

    RECOGNITION: shown the kanji, recall its meaning/reading.
    RECALL:      shown the meaning/reading, produce the kanji.
    STROKE:      reserved for the later handwriting-practice feature.
    """

    RECOGNITION = "recognition"
    RECALL = "recall"
    STROKE = "stroke"


class DeckKind(enum.StrEnum):
    KANJI = "kanji"
    VOCAB = "vocab"
    MIXED = "mixed"


class CardState(enum.StrEnum):
    """Lifecycle state of a card, mirrored from the SRS engine.

    ``NEW`` is our own marker for a card that has never been answered; once
    reviewed a card is always LEARNING / REVIEW / RELEARNING (matching FSRS).
    """

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"


class Rating(enum.IntEnum):
    """Grade the learner gives their own answer. Values match FSRS."""

    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


@dataclass(frozen=True, slots=True)
class Reading:
    type: ReadingType
    value: str


@dataclass(frozen=True, slots=True)
class Meaning:
    value: str
    lang: str = "en"


@dataclass(frozen=True, slots=True)
class Kanji:
    id: int
    literal: str
    stroke_count: int
    meanings: tuple[Meaning, ...] = ()
    readings: tuple[Reading, ...] = ()
    grade: int | None = None
    jlpt: int | None = None
    jlpt_old: int | None = None
    frequency: int | None = None
    radical: str | None = None

    def readings_of(self, kind: ReadingType) -> tuple[str, ...]:
        return tuple(r.value for r in self.readings if r.type == kind)


@dataclass(frozen=True, slots=True)
class Vocab:
    id: int
    expression: str
    kana: str
    glosses: tuple[str, ...] = ()
    jlpt: int | None = None
    kanji_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class Deck:
    id: int
    name: str
    kind: DeckKind = DeckKind.KANJI
    description: str = ""
    new_per_day: int = 10
    reviews_per_day: int = 200
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SchedulingState:
    """The SRS bookkeeping for a card.

    ``stability`` / ``difficulty`` are ``None`` until the first review. ``step``
    is FSRS's learning/relearning step index. ``reps`` and ``lapses`` are our
    own running totals (FSRS 6 no longer tracks them on the card).
    """

    state: CardState
    step: int
    due: datetime
    stability: float | None
    difficulty: float | None
    reps: int
    lapses: int
    last_reviewed_at: datetime | None = None

    @property
    def is_new(self) -> bool:
        return self.state == CardState.NEW


@dataclass(frozen=True, slots=True)
class Card:
    id: int
    deck_id: int
    subject_type: SubjectType
    subject_id: int
    mode: CardMode
    scheduling: SchedulingState
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReviewLog:
    """One answered review. Enough is stored to re-optimise SRS params later."""

    id: int
    card_id: int
    reviewed_at: datetime
    rating: Rating
    elapsed_ms: int
    prev_due: datetime
    new_due: datetime
    prev_stability: float
    new_stability: float
