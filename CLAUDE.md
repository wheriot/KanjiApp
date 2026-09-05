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
uv run python -m scripts.build_db    # rebuild kanji_app/resources/kanji.db
```

Run `scripts/check.py` and make it green before considering a change done.

## Testing

- `core/` and `services/`: fast unit tests, no DB, no Qt.
- `data/`: tests use the in-memory `conn` fixture (`tests/conftest.py`).
- `ui/`: light smoke tests only (constructs, signals) — don't over-invest.
- Every behavioural change lands with a test.

## Data pipeline (`scripts/`, dev-only, not shipped)

- `scripts/build_db.py` orchestrates; `import_kanjidic.py` / `import_kanjivg.py`
  do the work; `_common.py` has shared helpers.
- Run as modules: `uv run python -m scripts.build_db`.
- The pipeline is scoped to a **charset file** (`resources/jlpt/n5.txt`) — one
  kanji per line, `#` comments allowed. Add more list files to widen coverage.
- Sources are cached under `resources/_cache/` (gitignored). `kanji.db` itself
  IS committed.
- Importer tests seed the DB with SQL fixtures (`kanji_db` fixture); they don't
  run the network importers, except `test_import_kanjidic.py` which parses a
  small inline XML sample.

## UI wiring (as of Phase 2)

- `ui/app.py` builds a `KanjiCatalog` from the bundled `kanji.db` and hands it to
  `MainWindow`, which owns the screen stack and closes the catalog on exit.
- Browse screen: `BrowserView` ← `CatalogViewModel` ← `KanjiCatalog` (service).
  Views never import `data`; the view-model exposes plain properties + two Qt
  signals (`results_changed`, `selection_changed`).
- `StrokeOrderWidget` renders SVG from `core/kanjivg.render()` through a
  `QSvgRenderer` — no font dependency. `_Canvas.paintEvent` does the drawing.
- Tests: services/view-models use the `kanji_db` SQL fixture; widget/view tests
  call `build_app([])` first (Qt runs `offscreen`, set in `conftest.py`).

## Not yet built

`Dashboard` / `Review` / `Stats` / `Settings` screens are placeholders. The
`review_session` / SRS-loop wiring starts in Phase 3. Don't scaffold ahead of
the current phase.
