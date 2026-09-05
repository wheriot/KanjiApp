"""Shared test fixtures."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

# Run Qt without a real display so the UI smoke tests work in CI / headless envs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from kanji_app.config import BUNDLED_DB
from kanji_app.data import db
from kanji_app.data.repositories import KanjiRepo
from kanji_app.services.study import StudyService, open_study_service


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = db.connect(":memory:")
    db.migrate(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def kanji_db(conn: sqlite3.Connection) -> sqlite3.Connection:
    """An in-memory DB seeded with a handful of kanji, by SQL (no importers)."""
    conn.executescript(
        """
        INSERT INTO kanji (id, literal, stroke_count, grade, jlpt, jlpt_old, frequency, radical)
        VALUES
            (1, '水', 4, 1, 5, 4, 223, '85'),
            (2, '山', 3, 1, 5, 4, NULL, NULL),
            (3, '一', 1, 1, 5, 4, 2, '1');

        INSERT INTO reading (kanji_id, type, value) VALUES
            (1, 'on', 'スイ'), (1, 'kun', 'みず'),
            (2, 'on', 'サン'), (2, 'kun', 'やま'),
            (3, 'on', 'イチ'), (3, 'kun', 'ひと');

        INSERT INTO meaning (kanji_id, value, lang) VALUES
            (1, 'water', 'en'),
            (2, 'mountain', 'en'),
            (3, 'one', 'en'), (3, 'single', 'en');

        INSERT INTO kanjivg (kanji_id, stroke_count, svg) VALUES
            (1, 4, '<svg id="mizu"/>'),
            (2, 3, '<svg id="yama"/>');
        """
    )
    return conn


@pytest.fixture
def reference_repo() -> Iterator[KanjiRepo]:
    """KanjiRepo over the real shipped kanji.db."""
    connection = db.connect(BUNDLED_DB)
    db.migrate(connection)
    try:
        yield KanjiRepo(connection)
    finally:
        connection.close()


@pytest.fixture
def study_service(tmp_path: Path) -> Iterator[StudyService]:
    """A StudyService with a fresh study.db and the real reference kanji.db."""
    service = open_study_service(tmp_path)
    try:
        yield service
    finally:
        service.close()
