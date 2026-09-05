"""Database connection and schema migration.

This module owns *how* we talk to SQLite (connection settings, applying the
schema). Query logic belongs in :mod:`kanji_app.data.repositories`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Bump when schema.sql changes in a way that needs a migration step. For now the
# schema is created idempotently and there are no historical versions to upgrade.
SCHEMA_VERSION = 1


def connect(database: Path | str) -> sqlite3.Connection:
    """Open a tuned connection. Pass ``":memory:"`` for tests."""
    conn = sqlite3.connect(database, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply the schema and record its version. Safe to call on every startup."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    elif row["version"] != SCHEMA_VERSION:
        conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block inside BEGIN/COMMIT, rolling back on error."""
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
