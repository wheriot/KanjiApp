# CLAUDE.md — working rules for this repo

Read this before editing. It exists so changes stay small, typed, and testable.

## What this is

A desktop spaced-repetition app for learning Japanese kanji. Python + PySide6 +
SQLite + FSRS. Full design and roadmap: **[PLAN.md](PLAN.md)**. Current phase is
noted in [README.md](README.md).

## Architecture — the dependency rule

```
ui  ->  ui.view_models  ->  services  ->  core / data
```

- **`kanji_app/core/`** — pure domain logic. No Qt. No SQL. No filesystem.
  May use plain libraries (e.g. `fsrs`), but wrap them so the rest of the app
  depends on our interface, not theirs (see `core/srs.py`).
- **`kanji_app/data/`** — SQLite. **Every SQL string lives in
  `data/repositories.py`** (or `schema.sql`). Nothing else runs SQL.
- **`kanji_app/services/`** — use-cases that combine `core` + `data`. No Qt.
- **`kanji_app/ui/`** — PySide6. Views talk to view-models; view-models talk to
  services. Views never import `data` or touch SQLite.

Never add an import that points "up" this list.

## Conventions

- Target Python 3.12+. `from __future__ import annotations` at the top of every
  module. Full type hints — `mypy` runs in `strict` mode.
- Keep modules small and single-purpose (aim < ~200 lines). One class/concern
  per file.
- Prefer pure functions and frozen dataclasses in `core/`.
- One-line (or short) module docstring saying the module's role in the layering.
- Datetimes are timezone-aware UTC everywhere (`datetime.now(UTC)`).
- Match the surrounding style; don't introduce new dependencies without a note
  in PLAN.md.

## Data model

Defined once in `kanji_app/data/schema.sql`; mirrored by dataclasses in
`kanji_app/core/models.py`. The schema is intentionally generic:

- a `card` references a subject via `(subject_type, subject_id)` so vocab cards
  need no schema change later;
- `deck` is a real table even though the MVP ships one deck.

Do not "simplify" these away — see PLAN.md "capability now, surface later".

## Commands

```
uv sync                              # install
uv run kanji-app                     # run the app
uv run python scripts/check.py       # ruff + ruff format + mypy + pytest
uv run pytest                        # tests only
```

Run `scripts/check.py` and make it green before considering a change done.

## Testing

- `core/` and `services/`: fast unit tests, no DB, no Qt.
- `data/`: tests use the in-memory `conn` fixture (`tests/conftest.py`).
- `ui/`: light smoke tests only (constructs, signals) — don't over-invest.
- Every behavioural change lands with a test.

## Not yet built

`services/`, `ui/view_models/`, most of `ui/`, the data importers, and
`data/repositories.py` are stubs or empty. Build them phase by phase per
PLAN.md — don't scaffold ahead of the current phase.
