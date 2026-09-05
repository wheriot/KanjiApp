"""Repositories — the only place in the app that runs SQL.

Each repository wraps a :class:`sqlite3.Connection` and returns ``core.models``
objects. Keep query strings here; keep business rules in ``core`` / ``services``.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Sequence

from kanji_app.core.models import Kanji, Meaning, Reading, ReadingType


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

    def list_by_jlpt(self, level: int) -> list[Kanji]:
        rows = self._conn.execute(
            "SELECT * FROM kanji WHERE jlpt = ? ORDER BY frequency IS NULL, frequency, literal",
            (level,),
        ).fetchall()
        return self._hydrate(rows)

    def list_by_grade(self, grade: int) -> list[Kanji]:
        rows = self._conn.execute(
            "SELECT * FROM kanji WHERE grade = ? ORDER BY frequency IS NULL, frequency, literal",
            (grade,),
        ).fetchall()
        return self._hydrate(rows)

    def list_by_stroke_count(self, strokes: int) -> list[Kanji]:
        rows = self._conn.execute(
            "SELECT * FROM kanji WHERE stroke_count = ? ORDER BY literal", (strokes,)
        ).fetchall()
        return self._hydrate(rows)

    def all(self) -> list[Kanji]:
        rows = self._conn.execute("SELECT * FROM kanji ORDER BY literal").fetchall()
        return self._hydrate(rows)

    def search(self, query: str, limit: int = 50) -> list[Kanji]:
        """Match a single kanji character, an English meaning, or a reading."""
        query = query.strip()
        if not query:
            return []
        like = f"%{query}%"
        rows = self._conn.execute(
            """
            SELECT DISTINCT k.*
            FROM kanji k
            LEFT JOIN meaning m ON m.kanji_id = k.id
            LEFT JOIN reading r ON r.kanji_id = k.id
            WHERE k.literal = :exact
               OR m.value LIKE :like
               OR r.value LIKE :like
            ORDER BY k.frequency IS NULL, k.frequency, k.literal
            LIMIT :limit
            """,
            {"exact": query, "like": like, "limit": limit},
        ).fetchall()
        return self._hydrate(rows)

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
