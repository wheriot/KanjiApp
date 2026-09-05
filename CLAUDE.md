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

## Study data (Phase 3)

- Two databases: the **reference** `kanji.db` (bundled, read-only use) and the
  **study** `study.db` (per-user data dir, writable — decks/cards/review_log).
  `StudyService` holds one connection to each. They never join.
- All datetimes are UTC ISO strings in SQLite; `_iso` / `_dt` in `repositories.py`.
- Daily new/review tallies are derived from `review_log`, not counters.
- `core/review_session.py` is pure; `StudyService` is the stateful orchestrator;
  `ReviewViewModel` tracks cursor + reveal state.

## Stats (Phase 4)

- `services/stats.py` (`StatsService`) reads `review_log` + card states and
  returns a `StatsReport`. Day bucketing uses `core.review_session.day_start`
  (04:00 boundary). "Mature" reviews (for retention) are those with
  `prev_stability > 0` — i.e. not a card's first review.
- `StudyService.stats_service()` builds one sharing the same two connections.
- `MainWindow` refreshes Dashboard/Review/Stats on screen-change and on
  `catalog_vm.deck_changed`.

## Settings & theme (Phase 5)

- `services/settings.py` (`AppSettings`/`SettingsStore`) persists to the `setting`
  table. `StudyService` owns the store, applies `fsrs_retention` to its
  `FsrsScheduler`, and rebuilds it on `update_settings`.
- `ui/theme.py`: `apply_theme` (via `QStyleHints.setColorScheme`) and `load_fonts`
  (registers `assets/fonts/*`, else OS fallback). `assets/fonts/` is gitignored;
  `scripts/fetch_font.py` populates it.
- Per-deck limits live on the `deck` row; the Settings screen edits the current deck.

## Vocabulary (Phase 7)

- `scripts/import_jmdict.py` builds a narrow N5 subset; `VocabRepo` + catalog
  vocab methods; the Browse screen is a Kanji/Vocabulary `QTabWidget`.
- `StudyService._to_item` renders each card to a `ReviewItem` with plain-text
  faces (`prompt` / `prompt_note` / `answer` / `answer_note` + optional
  `stroke`). `CardFace` is subject-agnostic — no card-mode branching in the UI.
- `add_vocab` mirrors `add_kanji` (both go through `_add_subject`).

## Roadmap status

Phases 0–7 are done. Remaining items live under PLAN.md "Later / optional"
(Tatoeba sentences, PyInstaller build, handwriting, audio). Widening past N5 is
just adding `resources/jlpt/n4.txt` etc. and rerunning `scripts.build_db`.
