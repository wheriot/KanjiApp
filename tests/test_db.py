from __future__ import annotations

import sqlite3

import pytest
from kanji_app.data import db


def test_migrate_is_idempotent(conn: sqlite3.Connection) -> None:
    db.migrate(conn)  # second call on top of the fixture's first
    version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
    assert version == db.SCHEMA_VERSION


def test_core_tables_exist(conn: sqlite3.Connection) -> None:
    names = {
        row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"kanji", "reading", "meaning", "deck", "card", "review_log"} <= names


def test_card_unique_constraint(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO deck (id, name) VALUES (1, 'Default')")
    conn.execute(
        "INSERT INTO card (deck_id, subject_type, subject_id, mode, due) "
        "VALUES (1, 'kanji', 42, 'recognition', '2026-01-01')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO card (deck_id, subject_type, subject_id, mode, due) "
            "VALUES (1, 'kanji', 42, 'recognition', '2026-01-02')"
        )


def test_foreign_keys_enforced(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO card (deck_id, subject_type, subject_id, mode, due) "
            "VALUES (999, 'kanji', 1, 'recall', '2026-01-01')"
        )
