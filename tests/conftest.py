"""Shared test fixtures."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator

import pytest

# Run Qt without a real display so the UI smoke tests work in CI / headless envs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from kanji_app.data import db


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = db.connect(":memory:")
    db.migrate(connection)
    try:
        yield connection
    finally:
        connection.close()
