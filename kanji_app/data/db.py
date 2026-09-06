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

# Bump when schema.sql changes in a way that needs a migration step.
SCHEMA_VERSION = 1

# Columns added to existing tables after their first release. ``CREATE TABLE IF
# NOT EXISTS`` won't add them, so we ALTER them in before running the schema — it
# keeps a bundled kanji.db that predates a column working until it's rebuilt.
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (("vocab", "grade", "INTEGER"),)


def connect(database: Path | str) -> sqlite3.Connection:
    """Open a tuned connection. Pass ``":memory:"`` for tests."""
    conn = sqlite3.connect(database, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply the schema and record its version. Safe to call on every startup."""
    _add_missing_columns(conn)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    elif row["version"] != SCHEMA_VERSION:
        conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))


def _add_missing_columns(conn: sqlite3.Connection) -> None:
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, column, decl in _ADDED_COLUMNS:
        if table not in tables:
            continue
        columns = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


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
