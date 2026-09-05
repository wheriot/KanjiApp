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
