"""Repositories — the only place in the app that runs SQL.

Each repository wraps a :class:`sqlite3.Connection` and returns ``core.models``
objects. Keep query strings here; keep business rules in ``core`` / ``services``.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime

from kanji_app.core.models import (
    Card,
    CardMode,
    CardState,
    Deck,
    DeckKind,
    Kanji,
    Meaning,
    Rating,
    Reading,
    ReadingType,
    SchedulingState,
    SubjectType,
    Vocab,
)
from kanji_app.core.srs import ReviewResult


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def _dt(text: str) -> datetime:
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _new_id(cursor: sqlite3.Cursor) -> int:
    row_id = cursor.lastrowid
    assert row_id is not None
    return row_id


class KanjiRepo:
    """Read access to the reference kanji dictionary."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # -- single lookups ------------------------------------------------------

    def get(self, kanji_id: int) -> Kanji | None:
        row = self._conn.execute("SELECT * FROM kanji WHERE id = ?", (kanji_id,)).fetchone()
        return self._hydrate([row])[0] if row else None

    def get_by_literal(self, literal: str) -> Kanji | None:
        row = self._conn.execute("SELECT * FROM kanji WHERE literal = ?", (literal,)).fetchone()
        return self._hydrate([row])[0] if row else None

    # -- list queries -------------------------------------------------------

    def find(
        self,
        *,
        text: str = "",
        jlpt: int | None = None,
        grade: int | None = None,
        stroke_count: int | None = None,
        limit: int = 500,
    ) -> list[Kanji]:
        """Filtered kanji list. ``text`` matches a literal, meaning, or reading.

        Results are ordered by newspaper frequency (most common first, unranked
        last), then by literal.
        """
        conditions: list[str] = []
        params: dict[str, object] = {"limit": limit}

        text = text.strip()
        if text:
            conditions.append(
                "(k.literal = :exact"
                " OR EXISTS (SELECT 1 FROM meaning m WHERE m.kanji_id = k.id"
                "            AND m.value LIKE :like)"
                " OR EXISTS (SELECT 1 FROM reading r WHERE r.kanji_id = k.id"
                "            AND r.value LIKE :like))"
            )
            params["exact"] = text
            params["like"] = f"%{text}%"
        if jlpt is not None:
            conditions.append("k.jlpt = :jlpt")
            params["jlpt"] = jlpt
        if grade is not None:
            conditions.append("k.grade = :grade")
            params["grade"] = grade
        if stroke_count is not None:
            conditions.append("k.stroke_count = :strokes")
            params["strokes"] = stroke_count

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._conn.execute(
            f"SELECT k.* FROM kanji k {where} "
            "ORDER BY k.frequency IS NULL, k.frequency, k.literal LIMIT :limit",
            params,
        ).fetchall()
        return self._hydrate(rows)

    def search(self, query: str, limit: int = 50) -> list[Kanji]:
        """Match a single kanji character, an English meaning, or a reading."""
        if not query.strip():
            return []
        return self.find(text=query, limit=limit)

    def all(self) -> list[Kanji]:
        return self.find()

    def distinct_values(self, column: str) -> list[int]:
        """Sorted distinct non-null values of ``jlpt``, ``grade``, or ``stroke_count``."""
        if column not in {"jlpt", "grade", "stroke_count"}:
            raise ValueError(f"not a filterable column: {column}")
        rows = self._conn.execute(
            f"SELECT DISTINCT {column} AS v FROM kanji WHERE {column} IS NOT NULL ORDER BY v"
        ).fetchall()
        return [int(r["v"]) for r in rows]

    def count_by_jlpt(self) -> dict[int, int]:
        rows = self._conn.execute(
            "SELECT jlpt, COUNT(*) AS n FROM kanji WHERE jlpt IS NOT NULL GROUP BY jlpt"
        ).fetchall()
        return {int(r["jlpt"]): int(r["n"]) for r in rows}

    def jlpt_by_id(self, ids: Iterable[int]) -> dict[int, int | None]:
        ids = list(ids)
        if not ids:
            return {}
        rows = self._conn.execute(
            f"SELECT id, jlpt FROM kanji WHERE id IN ({_marks(ids)})", tuple(ids)
        ).fetchall()
        return {int(r["id"]): r["jlpt"] for r in rows}

    # -- stroke order -----------------------------------------------------

    def stroke_svg(self, kanji_id: int) -> str | None:
        row = self._conn.execute(
            "SELECT svg FROM kanjivg WHERE kanji_id = ?", (kanji_id,)
        ).fetchone()
        return row["svg"] if row else None

    # -- stats -----------------------------------------------------------

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM kanji").fetchone()[0])

    # -- hydration ------------------------------------------------------

    def _hydrate(self, rows: Sequence[sqlite3.Row]) -> list[Kanji]:
        rows = [r for r in rows if r is not None]
        if not rows:
            return []
        ids = [r["id"] for r in rows]
        readings = self._readings_for(ids)
        meanings = self._meanings_for(ids)
        return [
            Kanji(
                id=r["id"],
                literal=r["literal"],
                stroke_count=r["stroke_count"],
                grade=r["grade"],
                jlpt=r["jlpt"],
                jlpt_old=r["jlpt_old"],
                frequency=r["frequency"],
                radical=r["radical"],
                readings=tuple(readings.get(r["id"], ())),
                meanings=tuple(meanings.get(r["id"], ())),
            )
            for r in rows
        ]

    def _readings_for(self, ids: Iterable[int]) -> dict[int, list[Reading]]:
        out: dict[int, list[Reading]] = defaultdict(list)
        for row in self._conn.execute(
            f"SELECT kanji_id, type, value FROM reading WHERE kanji_id IN ({_marks(ids)})",
            tuple(ids),
        ):
            out[row["kanji_id"]].append(Reading(ReadingType(row["type"]), row["value"]))
        return out

    def _meanings_for(self, ids: Iterable[int]) -> dict[int, list[Meaning]]:
        out: dict[int, list[Meaning]] = defaultdict(list)
        for row in self._conn.execute(
            f"SELECT kanji_id, value, lang FROM meaning WHERE kanji_id IN ({_marks(ids)})",
            tuple(ids),
        ):
            out[row["kanji_id"]].append(Meaning(row["value"], row["lang"]))
        return out


def _marks(items: Iterable[object]) -> str:
    return ", ".join("?" for _ in items)


class VocabRepo:
    """Read access to the reference vocabulary list."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, vocab_id: int) -> Vocab | None:
        row = self._conn.execute("SELECT * FROM vocab WHERE id = ?", (vocab_id,)).fetchone()
        return self._hydrate([row])[0] if row else None

    def find(self, text: str = "", limit: int = 500) -> list[Vocab]:
        text = text.strip()
        if text:
            like = f"%{text}%"
            rows = self._conn.execute(
                """
                SELECT DISTINCT v.* FROM vocab v
                LEFT JOIN vocab_gloss g ON g.vocab_id = v.id
                WHERE v.expression LIKE :like OR v.kana LIKE :like OR g.value LIKE :like
                ORDER BY length(v.expression), v.expression
                LIMIT :limit
                """,
                {"like": like, "limit": limit},
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM vocab ORDER BY length(expression), expression LIMIT ?",
                (limit,),
            ).fetchall()
        return self._hydrate(rows)

    def for_kanji(self, kanji_id: int, limit: int = 30) -> list[Vocab]:
        rows = self._conn.execute(
            """
            SELECT v.* FROM vocab v
            JOIN vocab_kanji vk ON vk.vocab_id = v.id
            WHERE vk.kanji_id = ?
            ORDER BY length(v.expression), v.expression
            LIMIT ?
            """,
            (kanji_id, limit),
        ).fetchall()
        return self._hydrate(rows)

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0])

    def _hydrate(self, rows: Sequence[sqlite3.Row]) -> list[Vocab]:
        rows = [r for r in rows if r is not None]
        if not rows:
            return []
        ids = [r["id"] for r in rows]
        glosses: dict[int, list[str]] = defaultdict(list)
        for g in self._conn.execute(
            f"SELECT vocab_id, value FROM vocab_gloss WHERE vocab_id IN ({_marks(ids)})",
            tuple(ids),
        ):
            glosses[g["vocab_id"]].append(g["value"])
        links: dict[int, list[int]] = defaultdict(list)
        for link in self._conn.execute(
            f"SELECT vocab_id, kanji_id FROM vocab_kanji WHERE vocab_id IN ({_marks(ids)})",
            tuple(ids),
        ):
            links[link["vocab_id"]].append(link["kanji_id"])
        return [
            Vocab(
                id=r["id"],
                expression=r["expression"],
                kana=r["kana"],
                jlpt=r["jlpt"],
                glosses=tuple(glosses.get(r["id"], ())),
                kanji_ids=tuple(links.get(r["id"], ())),
            )
            for r in rows
        ]


class DeckRepo:
    """Study decks (lives in the writable study database)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def all(self) -> list[Deck]:
        rows = self._conn.execute("SELECT * FROM deck ORDER BY created_at, id").fetchall()
        return [self._row(r) for r in rows]

    def get(self, deck_id: int) -> Deck | None:
        row = self._conn.execute("SELECT * FROM deck WHERE id = ?", (deck_id,)).fetchone()
        return self._row(row) if row else None

    def create(self, name: str, *, kind: DeckKind = DeckKind.KANJI, description: str = "") -> Deck:
        cursor = self._conn.execute(
            "INSERT INTO deck (name, kind, description) VALUES (?, ?, ?)",
            (name, kind.value, description),
        )
        created = self.get(_new_id(cursor))
        assert created is not None
        return created

    def ensure_default(self) -> Deck:
        existing = self.all()
        return existing[0] if existing else self.create("My N5 Kanji")

    def update(
        self,
        deck_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        new_per_day: int | None = None,
        reviews_per_day: int | None = None,
    ) -> Deck:
        current = self.get(deck_id)
        assert current is not None
        self._conn.execute(
            """
            UPDATE deck SET name = ?, description = ?, new_per_day = ?, reviews_per_day = ?
            WHERE id = ?
            """,
            (
                name if name is not None else current.name,
                description if description is not None else current.description,
                new_per_day if new_per_day is not None else current.new_per_day,
                reviews_per_day if reviews_per_day is not None else current.reviews_per_day,
                deck_id,
            ),
        )
        updated = self.get(deck_id)
        assert updated is not None
        return updated

    def delete(self, deck_id: int) -> None:
        self._conn.execute("DELETE FROM deck WHERE id = ?", (deck_id,))

    @staticmethod
    def _row(row: sqlite3.Row) -> Deck:
        return Deck(
            id=row["id"],
            name=row["name"],
            kind=DeckKind(row["kind"]),
            description=row["description"],
            new_per_day=row["new_per_day"],
            reviews_per_day=row["reviews_per_day"],
            created_at=_dt(row["created_at"]) if row["created_at"] else None,
        )


class CardRepo:
    """Flashcards and their SRS scheduling state."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def for_deck(self, deck_id: int) -> list[Card]:
        rows = self._conn.execute(
            "SELECT * FROM card WHERE deck_id = ? ORDER BY id", (deck_id,)
        ).fetchall()
        return [self._row(r) for r in rows]

    def count_for_deck(self, deck_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM card WHERE deck_id = ?", (deck_id,)
        ).fetchone()
        return int(row[0])

    def get(self, card_id: int) -> Card | None:
        row = self._conn.execute("SELECT * FROM card WHERE id = ?", (card_id,)).fetchone()
        return self._row(row) if row else None

    def modes_for_subject(
        self, deck_id: int, subject_type: SubjectType, subject_id: int
    ) -> set[CardMode]:
        rows = self._conn.execute(
            "SELECT mode FROM card WHERE deck_id = ? AND subject_type = ? AND subject_id = ?",
            (deck_id, subject_type.value, subject_id),
        ).fetchall()
        return {CardMode(r["mode"]) for r in rows}

    def create(
        self,
        deck_id: int,
        subject_type: SubjectType,
        subject_id: int,
        mode: CardMode,
        scheduling: SchedulingState,
    ) -> Card:
        cursor = self._conn.execute(
            """
            INSERT INTO card (deck_id, subject_type, subject_id, mode,
                              state, step, due, stability, difficulty, reps, lapses)
            VALUES (:deck_id, :subject_type, :subject_id, :mode,
                    :state, :step, :due, :stability, :difficulty, :reps, :lapses)
            """,
            {
                "deck_id": deck_id,
                "subject_type": subject_type.value,
                "subject_id": subject_id,
                "mode": mode.value,
                **_scheduling_params(scheduling),
            },
        )
        created = self.get(_new_id(cursor))
        assert created is not None
        return created

    def update_scheduling(self, card_id: int, scheduling: SchedulingState) -> None:
        self._conn.execute(
            """
            UPDATE card SET state = :state, step = :step, due = :due,
                            stability = :stability, difficulty = :difficulty,
                            reps = :reps, lapses = :lapses,
                            last_reviewed_at = :last_reviewed_at
            WHERE id = :id
            """,
            {"id": card_id, **_scheduling_params(scheduling)},
        )

    # -- aggregates (for stats) ------------------------------------

    def state_breakdown(self, deck_id: int) -> dict[CardState, int]:
        rows = self._conn.execute(
            "SELECT state, COUNT(*) AS n FROM card WHERE deck_id = ? GROUP BY state",
            (deck_id,),
        ).fetchall()
        return {CardState(r["state"]): int(r["n"]) for r in rows}

    def subject_ids(self, deck_id: int, *, learned_only: bool = False) -> set[int]:
        """Distinct kanji ids with a card in this deck (optionally past the 'new' stage)."""
        clause = "AND state != 'new'" if learned_only else ""
        rows = self._conn.execute(
            f"SELECT DISTINCT subject_id FROM card "
            f"WHERE deck_id = ? AND subject_type = 'kanji' {clause}",
            (deck_id,),
        ).fetchall()
        return {int(r["subject_id"]) for r in rows}

    def due_dates_between(self, deck_id: int, start: datetime, end: datetime) -> list[datetime]:
        rows = self._conn.execute(
            """
            SELECT due FROM card
            WHERE deck_id = ? AND state != 'new' AND due >= ? AND due < ?
            """,
            (deck_id, _iso(start), _iso(end)),
        ).fetchall()
        return [_dt(r["due"]) for r in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> Card:
        scheduling = SchedulingState(
            state=CardState(row["state"]),
            step=row["step"],
            due=_dt(row["due"]),
            stability=row["stability"],
            difficulty=row["difficulty"],
            reps=row["reps"],
            lapses=row["lapses"],
            last_reviewed_at=_dt(row["last_reviewed_at"]) if row["last_reviewed_at"] else None,
        )
        return Card(
            id=row["id"],
            deck_id=row["deck_id"],
            subject_type=SubjectType(row["subject_type"]),
            subject_id=row["subject_id"],
            mode=CardMode(row["mode"]),
            scheduling=scheduling,
            created_at=_dt(row["created_at"]) if row["created_at"] else None,
        )


class ReviewLogRepo:
    """Append-only record of answered reviews."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(
        self,
        card_id: int,
        rating: Rating,
        result: ReviewResult,
        reviewed_at: datetime,
        elapsed_ms: int = 0,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO review_log (card_id, reviewed_at, rating, elapsed_ms,
                                    prev_due, new_due, prev_stability, new_stability)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                _iso(reviewed_at),
                int(rating),
                elapsed_ms,
                _iso(result.previous_due),
                _iso(result.state.due),
                result.previous_stability,
                result.new_stability,
            ),
        )

    def count_since(self, deck_id: int, since: datetime) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) FROM review_log rl
            JOIN card c ON c.id = rl.card_id
            WHERE c.deck_id = ? AND rl.reviewed_at >= ?
            """,
            (deck_id, _iso(since)),
        ).fetchone()
        return int(row[0])

    def count_new_since(self, deck_id: int, since: datetime) -> int:
        """Cards first introduced today (their first review has prev_stability 0)."""
        row = self._conn.execute(
            """
            SELECT COUNT(*) FROM review_log rl
            JOIN card c ON c.id = rl.card_id
            WHERE c.deck_id = ? AND rl.reviewed_at >= ? AND rl.prev_stability = 0
            """,
            (deck_id, _iso(since)),
        ).fetchone()
        return int(row[0])

    def timestamps_since(self, deck_id: int, since: datetime) -> list[datetime]:
        rows = self._conn.execute(
            """
            SELECT rl.reviewed_at FROM review_log rl
            JOIN card c ON c.id = rl.card_id
            WHERE c.deck_id = ? AND rl.reviewed_at >= ?
            ORDER BY rl.reviewed_at
            """,
            (deck_id, _iso(since)),
        ).fetchall()
        return [_dt(r["reviewed_at"]) for r in rows]

    def retention_since(self, deck_id: int, since: datetime) -> tuple[int, int]:
        """(passed, total) over reviews of already-learned cards (prev_stability > 0).

        A review counts as passed when it was not rated "Again".
        """
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN rl.rating != 1 THEN 1 ELSE 0 END) AS passed
            FROM review_log rl
            JOIN card c ON c.id = rl.card_id
            WHERE c.deck_id = ? AND rl.reviewed_at >= ? AND rl.prev_stability > 0
            """,
            (deck_id, _iso(since)),
        ).fetchone()
        total = int(row["total"])
        return (int(row["passed"] or 0), total)


class SettingsRepo:
    """The ``setting`` key/value table in the study database."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM setting WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO setting (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def all(self) -> dict[str, str]:
        return {r["key"]: r["value"] for r in self._conn.execute("SELECT key, value FROM setting")}


def _scheduling_params(s: SchedulingState) -> dict[str, object]:
    return {
        "state": s.state.value,
        "step": s.step,
        "due": _iso(s.due),
        "stability": s.stability,
        "difficulty": s.difficulty,
        "reps": s.reps,
        "lapses": s.lapses,
        "last_reviewed_at": _iso(s.last_reviewed_at) if s.last_reviewed_at else None,
    }
