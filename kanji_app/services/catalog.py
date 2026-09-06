"""Kanji catalogue: the use-case layer behind the browser and detail screens.

Wraps a reference-database connection and exposes browsing/lookup in terms the
UI needs, without the UI touching ``data`` or SQL directly.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from kanji_app.config import BUNDLED_DB
from kanji_app.core.kanjivg import StrokeDrawing
from kanji_app.core.kanjivg import parse as parse_kanjivg
from kanji_app.core.models import Kanji, Sentence, Vocab
from kanji_app.data import db
from kanji_app.data.repositories import KanjiRepo, VocabRepo


@dataclass(frozen=True, slots=True)
class KanjiFilter:
    """A browser filter. Empty/``None`` fields are ignored."""

    text: str = ""
    jlpt: int | None = None
    grade: int | None = None
    stroke_count: int | None = None


@dataclass(frozen=True, slots=True)
class FilterOptions:
    """Values available to populate the filter controls."""

    jlpt: list[int]
    grade: list[int]
    stroke_count: list[int]


class KanjiCatalog:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._repo = KanjiRepo(conn)
        self._vocab = VocabRepo(conn)

    # -- kanji -------------------------------------------------------

    def browse(self, flt: KanjiFilter, limit: int = 5000) -> list[Kanji]:
        return self._repo.find(
            text=flt.text,
            jlpt=flt.jlpt,
            grade=flt.grade,
            stroke_count=flt.stroke_count,
            limit=limit,
        )

    def get(self, kanji_id: int) -> Kanji | None:
        return self._repo.get(kanji_id)

    def stroke_drawing(self, kanji_id: int) -> StrokeDrawing | None:
        svg = self._repo.stroke_svg(kanji_id)
        return parse_kanjivg(svg) if svg else None

    def filter_options(self) -> FilterOptions:
        return FilterOptions(
            jlpt=self._repo.distinct_values("jlpt"),
            grade=self._repo.distinct_values("grade"),
            stroke_count=self._repo.distinct_values("stroke_count"),
        )

    def total(self) -> int:
        return self._repo.count()

    # -- vocab ------------------------------------------------------

    def browse_vocab(self, text: str = "", limit: int = 2000) -> list[Vocab]:
        return self._vocab.find(text=text, limit=limit)

    def get_vocab(self, vocab_id: int) -> Vocab | None:
        return self._vocab.get(vocab_id)

    def vocab_for_kanji(self, kanji_id: int) -> list[Vocab]:
        return self._vocab.for_kanji(kanji_id)

    def vocab_sentences(self, vocab_id: int, limit: int = 3) -> list[Sentence]:
        return self._vocab.sentences_for(vocab_id, limit)

    def vocab_total(self) -> int:
        return self._vocab.count()

    def close(self) -> None:
        self._conn.close()


def open_bundled_catalog() -> KanjiCatalog:
    """Open the reference database that ships with the app (read-only usage)."""
    conn = db.connect(BUNDLED_DB)
    db.migrate(conn)
    return KanjiCatalog(conn)
