from __future__ import annotations

import sqlite3

from kanji_app.data.repositories import SettingsRepo
from kanji_app.services.settings import AppSettings, SettingsStore
from kanji_app.services.study import StudyService


def test_settings_repo_upsert(conn: sqlite3.Connection) -> None:
    repo = SettingsRepo(conn)
    assert repo.get("theme") is None
    repo.set("theme", "dark")
    repo.set("theme", "light")  # upsert, not a second row
    assert repo.get("theme") == "light"
    assert repo.all() == {"theme": "light"}


def test_settings_store_defaults_and_roundtrip(conn: sqlite3.Connection) -> None:
    store = SettingsStore(conn)
    assert store.load() == AppSettings(theme="system", fsrs_retention=0.90)

    store.save(AppSettings(theme="dark", fsrs_retention=0.93))
    assert store.load() == AppSettings(theme="dark", fsrs_retention=0.93)


def test_settings_normalisation(conn: sqlite3.Connection) -> None:
    store = SettingsStore(conn)
    saved = store.save(AppSettings(theme="chartreuse", fsrs_retention=0.5))
    assert saved.theme == "system"
    assert saved.fsrs_retention == 0.80  # clamped to the minimum


def test_study_service_applies_retention(study_service: StudyService) -> None:
    from kanji_app.core.srs import FsrsScheduler

    study_service.update_settings(AppSettings(theme="light", fsrs_retention=0.95))
    scheduler = study_service._scheduler
    assert isinstance(scheduler, FsrsScheduler)
    assert scheduler._engine.desired_retention == 0.95


def test_update_deck_limits(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    updated = study_service.update_deck(deck.id, new_per_day=25, reviews_per_day=500)
    assert updated.new_per_day == 25
    assert updated.reviews_per_day == 500
    assert study_service.default_deck().new_per_day == 25  # reloaded
