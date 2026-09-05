"""Study service: the use-case layer for adding cards and running review sessions.

Owns two SQLite connections:

- the **study** database (writable) — decks, cards, review logs
- the **reference** database (read-only use) — the shipped kanji dictionary

Keeping them separate means a ``git pull`` that ships a newer ``kanji.db`` is
picked up immediately, while the user's progress in ``study.db`` is untouched.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from kanji_app.config import BUNDLED_DB, Paths
from kanji_app.core import review_session
from kanji_app.core.models import Card, CardMode, Deck, Kanji, Rating, SubjectType
from kanji_app.core.review_session import DeckCounts
from kanji_app.core.srs import FsrsScheduler, Scheduler
from kanji_app.data import db
from kanji_app.data.repositories import CardRepo, DeckRepo, KanjiRepo, ReviewLogRepo
from kanji_app.services.settings import AppSettings, SettingsStore
from kanji_app.services.stats import StatsService

_STUDY_MODES = (CardMode.RECOGNITION, CardMode.RECALL)


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """A queued card together with the kanji it is about."""

    card: Card
    kanji: Kanji


@dataclass(frozen=True, slots=True)
class TodaySummary:
    """What the dashboard shows: work waiting and work already done today."""

    due: int
    new_available: int
    reviewed_today: int

    @property
    def waiting(self) -> int:
        return self.due + self.new_available


class StudyService:
    def __init__(
        self,
        study_conn: sqlite3.Connection,
        reference_conn: sqlite3.Connection,
        scheduler: Scheduler | None = None,
    ) -> None:
        self._study = study_conn
        self._reference = reference_conn
        self._decks = DeckRepo(study_conn)
        self._cards = CardRepo(study_conn)
        self._log = ReviewLogRepo(study_conn)
        self._kanji = KanjiRepo(reference_conn)
        self._settings_store = SettingsStore(study_conn)
        self._settings = self._settings_store.load()
        self._scheduler = scheduler or FsrsScheduler(self._settings.fsrs_retention)

    # -- settings ---------------------------------------------------

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def update_settings(self, new: AppSettings) -> AppSettings:
        self._settings = self._settings_store.save(new)
        # Only a scheduler built from a custom `scheduler=` arg is left alone.
        if isinstance(self._scheduler, FsrsScheduler):
            self._scheduler = FsrsScheduler(self._settings.fsrs_retention)
        return self._settings

    # -- decks --------------------------------------------------------

    def decks(self) -> list[Deck]:
        return self._decks.all()

    def default_deck(self) -> Deck:
        return self._decks.ensure_default()

    def get_deck(self, deck_id: int) -> Deck | None:
        return self._decks.get(deck_id)

    def create_deck(self, name: str) -> Deck:
        return self._decks.create(name)

    def update_deck(
        self,
        deck_id: int,
        *,
        name: str | None = None,
        new_per_day: int | None = None,
        reviews_per_day: int | None = None,
    ) -> Deck:
        return self._decks.update(
            deck_id, name=name, new_per_day=new_per_day, reviews_per_day=reviews_per_day
        )

    def delete_deck(self, deck_id: int) -> None:
        self._decks.delete(deck_id)

    def deck_card_count(self, deck_id: int) -> int:
        return self._cards.count_for_deck(deck_id)

    # -- building a collection --------------------------------------

    def is_in_deck(self, deck_id: int, kanji_id: int) -> bool:
        modes = self._cards.modes_for_subject(deck_id, SubjectType.KANJI, kanji_id)
        return set(_STUDY_MODES).issubset(modes)

    def add_kanji(self, deck_id: int, kanji_id: int, now: datetime | None = None) -> int:
        """Create the recognition + recall cards for a kanji. Returns cards added."""
        moment = now or datetime.now(UTC)
        existing = self._cards.modes_for_subject(deck_id, SubjectType.KANJI, kanji_id)
        added = 0
        with db.transaction(self._study):
            for mode in _STUDY_MODES:
                if mode not in existing:
                    self._cards.create(
                        deck_id,
                        SubjectType.KANJI,
                        kanji_id,
                        mode,
                        self._scheduler.new_state(moment),
                    )
                    added += 1
        return added

    # -- reviewing -------------------------------------------------

    def deck_counts(self, deck_id: int, now: datetime | None = None) -> DeckCounts:
        moment = now or datetime.now(UTC)
        return review_session.counts(self._cards.for_deck(deck_id), moment)

    def today_summary(self, deck_id: int, now: datetime | None = None) -> TodaySummary:
        moment = now or datetime.now(UTC)
        deck = self._decks.get(deck_id)
        raw = review_session.counts(self._cards.for_deck(deck_id), moment)
        if deck is None:
            return TodaySummary(due=raw.due, new_available=raw.new, reviewed_today=0)
        since = review_session.day_start(moment)
        new_done = self._log.count_new_since(deck_id, since)
        return TodaySummary(
            due=raw.due,
            new_available=max(0, min(raw.new, deck.new_per_day - new_done)),
            reviewed_today=self._log.count_since(deck_id, since),
        )

    def start_session(self, deck_id: int, now: datetime | None = None) -> list[ReviewItem]:
        moment = now or datetime.now(UTC)
        deck = self._decks.get(deck_id)
        if deck is None:
            return []
        since = review_session.day_start(moment)
        queue = review_session.build_queue(
            self._cards.for_deck(deck_id),
            now=moment,
            new_allowance=deck.new_per_day - self._log.count_new_since(deck_id, since),
            review_allowance=deck.reviews_per_day - self._log.count_since(deck_id, since),
        )
        return [item for card in queue if (item := self._to_item(card)) is not None]

    def answer(
        self,
        card: Card,
        rating: Rating,
        now: datetime | None = None,
        elapsed_ms: int = 0,
    ) -> None:
        moment = now or datetime.now(UTC)
        result = self._scheduler.review(card.scheduling, rating, moment)
        with db.transaction(self._study):
            self._cards.update_scheduling(card.id, result.state)
            self._log.record(card.id, rating, result, moment, elapsed_ms)

    # -- internals ------------------------------------------------

    def _to_item(self, card: Card) -> ReviewItem | None:
        if card.subject_type != SubjectType.KANJI:
            return None
        kanji = self._kanji.get(card.subject_id)
        return ReviewItem(card=card, kanji=kanji) if kanji else None

    def stats_service(self) -> StatsService:
        """A :class:`StatsService` sharing this service's two connections."""
        return StatsService(self._study, self._reference)

    def close(self) -> None:
        self._study.close()
        self._reference.close()


def open_study_service(data_dir: Path | None = None) -> StudyService:
    paths = Paths.resolve(data_dir)
    first_run = not paths.database.exists()
    paths.data_dir.mkdir(parents=True, exist_ok=True)

    study_conn = db.connect(paths.database)
    db.migrate(study_conn)
    if first_run:
        DeckRepo(study_conn).ensure_default()

    reference_conn = db.connect(BUNDLED_DB)
    db.migrate(reference_conn)
    return StudyService(study_conn, reference_conn)
