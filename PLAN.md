# Kanji Learning App — Development Plan

## 1. Goals & constraints

- **Primary language:** Python. Code should stay readable and easy to edit by hand or with Claude.
- **Runs with a GUI** (desktop app, offline-capable).
- **Built mostly with Claude** — so the codebase must be small-module, well-typed, well-tested, and documented so Claude can navigate it without loading everything.
- **Learning model:** spaced repetition (SRS) flashcards plus a browsable kanji dictionary and stroke-order reference.

### Decisions (locked)
- **GUI:** PySide6 (Qt).
- **SRS:** FSRS (`fsrs` package), wrapped behind our own thin interface.
- **Card types:** the schema and core support **kanji cards and vocab cards** from day one; the MVP only *builds and ships* kanji-only.
- **Decks:** the schema and core support **multiple decks** from day one; the MVP ships a **single default kanji deck**, with the multi-deck management UI added late.

### Assumptions (change these if wrong)
- Desktop only. Windows-first builds, but the code stays cross-platform (no Windows-only APIs); macOS/Linux builds are a later, low-effort add.
- Single local user, no accounts, no server.
- English-speaking learner studying Japanese.
- Handwriting/drawing practice is a "nice to have" for a later phase, not MVP.

**Guiding principle:** *capability now, surface later.* Build the data model and `core/` logic generically (any card type, any number of decks) so nothing needs re-architecting; just don't expose vocab or multi-deck UI until the final phases.

### Answered questions
- **Content:** target **JLPT N5** first (~80 kanji) — small enough to hand-verify the whole dataset.
- **Card modes:** ship **recognition and recall** from the MVP. Each studied kanji gets two cards: recognition (見る kanji → meaning/reading) and recall (meaning/reading → produce the kanji). Same FSRS scheduling, independent state.
- **Distribution:** whatever is least effort for the developer. Audience is just you + a Python-savvy friend, so **run from source** (`uv run kanji-app` / `python -m kanji_app`). No PyInstaller, no installer. A frozen build stays on the "later / optional" list if that ever changes.

## 2. Technology choices

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | Requirement; modern typing syntax |
| GUI | **PySide6 (Qt)** | Mature, huge docs, Claude knows it well, good for data-heavy views, real stroke-order/canvas support |
| Storage | SQLite via `sqlite3` (stdlib) + thin repository layer | Zero-config, single file, easy to inspect |
| SRS engine | **FSRS** (`fsrs` PyPI package), wrapped in our own `core/srs.py` interface | Modern, well-studied scheduling; the wrapper keeps FSRS out of `core`'s public API so it stays swappable/testable |
| Env/deps | `uv` | Fast, reproducible; `uv run kanji-app` is the whole install story for this audience |
| Testing | `pytest` | Standard |
| Lint/format | `ruff` + `ruff format`, `mypy` (or `pyright`) | Keeps Claude-generated code consistent |
| Config | `pydantic-settings` or a plain dataclass + TOML | Readable, validated |

## 3. Data sources (all free, check license/attribution)

| Data | Source | License note |
|---|---|---|
| Kanji readings, meanings, JLPT/grade/frequency | **KANJIDIC2** (EDRDG) | CC BY-SA 4.0 — attribution required |
| Stroke order / stroke paths (SVG) | **KanjiVG** | CC BY-SA 3.0 — attribution required |
| Vocabulary / example words | **JMdict** (EDRDG) | EDRDG license — attribution required |
| Example sentences | **Tatoeba** | CC BY 2.0 FR |
| Radical/component breakdown | KRADFILE / RADKFILE (EDRDG) | EDRDG license |

Plan: write one-off importer scripts (`scripts/import_*.py`) that parse these into our SQLite schema. Ship the pre-built `kanji.db` with the app; keep importers in the repo for rebuilds. Add a visible **Credits/Licenses** screen.

## 4. Architecture

GUI-agnostic core, thin UI on top. This keeps logic testable and lets Claude work on one layer at a time.

```
kanji_app/
  core/                  # pure Python, no Qt imports
    models.py            # dataclasses: Kanji, Reading, Card, ReviewLog, Deck
    srs.py               # scheduling wrapper (FSRS/SM-2), pure functions
    review_session.py    # queue building, "what's due", answer grading
    search.py            # kanji/vocab lookup & filtering logic
  data/
    db.py                # connection, migrations, schema version
    repositories.py      # KanjiRepo, CardRepo, ReviewLogRepo (SQL lives here only)
    schema.sql
  services/
    study_service.py     # orchestrates core + data for the UI (use-cases)
    stats_service.py     # progress, streaks, forecast
  ui/
    app.py               # QApplication bootstrap
    main_window.py
    views/
      dashboard_view.py
      review_view.py
      kanji_browser_view.py
      kanji_detail_view.py
      stats_view.py
      settings_view.py
    widgets/
      stroke_order_widget.py   # renders KanjiVG SVG, animates strokes
      card_widget.py
    view_models/          # per-view state, talks to services only
  assets/                 # icons, fonts (a CJK font, e.g. Noto Sans JP)
  scripts/                # import_kanjidic.py, import_kanjivg.py, build_db.py
  tests/                  # mirrors core/ and services/
  resources/kanji.db      # prebuilt
  config.py
  __main__.py             # python -m kanji_app
CLAUDE.md                 # architecture rules for Claude (see §8)
pyproject.toml
README.md
```

**Dependency rule:** `ui → view_models → services → core / data`. `core` imports nothing from the app except stdlib. Never put SQL outside `data/repositories.py`. Never import Qt in `core/` or `services/`.

## 5. Data model (first cut)

- **kanji**: id, literal, grade, jlpt, stroke_count, freq, radical, components
- **reading**: kanji_id, type (on/kun/nanori), value
- **meaning**: kanji_id, value, lang
- **vocab**: id, expression, kana, gloss, jlpt
- **vocab_kanji**: vocab_id, kanji_id (link)
- **deck**: id, name, description, kind (`kanji` | `vocab` | `mixed`), new_per_day, reviews_per_day, ordering strategy, created_at
  - MVP seeds one row: the default kanji deck. UI to add/edit/delete decks comes in Phase 6.
- **card**: id, deck_id, **subject_type** (`kanji` | `vocab`), **subject_id** (FK to kanji or vocab), card_mode (`recognition` | `recall` | `stroke`), state, due, stability, difficulty, reps, lapses, created_at
  - Polymorphic `subject_type`/`subject_id` is what lets vocab cards drop in later with zero schema change.
  - MVP creates two cards per added kanji: `card_mode = recognition` and `card_mode = recall`. `stroke` mode is reserved for the later handwriting feature.
  - Unique index on `(deck_id, subject_type, subject_id, card_mode)` to prevent dupes.
- **review_log**: id, card_id, ts, rating (again/hard/good/easy), elapsed_ms, prev_due, new_due, prev_stability, new_stability (keep enough to retrain FSRS params later)
- **setting**: key, value
- **schema_version**: single row

## 6. Feature roadmap

### Phase 0 — Skeleton (week 1)
- Repo scaffold, `pyproject.toml`, `ruff`/`mypy`/`pytest` config, CI-style local checks
- `CLAUDE.md`, `README.md`
- `core/models.py` + `data/db.py` with migration runner
- Blank PySide6 window that launches via `python -m kanji_app`
- **Exit check:** app opens, `pytest` green, `ruff`/`mypy` clean

### Phase 1 — Data pipeline (week 1–2)
- Importer scripts for KANJIDIC2 + KanjiVG + (subset of) JMdict
- Build `resources/kanji.db`
- `KanjiRepo` with lookup by literal, by JLPT, by grade, text search
- Tests against a small fixture DB
- **Exit check:** can query "all N5 kanji" and "detail for 水" from a REPL

### Phase 2 — Kanji browser (week 2–3)
- `kanji_browser_view`: grid/list, filter by JLPT/grade/stroke count, search box
- `kanji_detail_view`: readings, meanings, example vocab, frequency
- `stroke_order_widget`: static KanjiVG render first, then stroke-by-stroke animation
- **Exit check:** browse and inspect any kanji, see stroke order

### Phase 3 — SRS review loop (week 3–5) — core value
- `srs.py` wrapper around FSRS; `review_session.py` builds the due queue
- `review_view`: show prompt → reveal answer → rate (Again/Hard/Good/Easy)
- Card creation: "add this kanji to my study deck" from browser/detail — creates both a **recognition** and a **recall** card
- `card_widget` renders both modes (recognition shows the kanji; recall shows meaning + reading and asks for the kanji, self-graded)
- Persist `review_log`, update card scheduling
- Daily new-card limit + review limit in settings
- **Exit check:** study a session mixing recognition + recall cards, close app, reopen, correct cards are due

### Phase 4 — Dashboard & stats (week 5–6)
- Dashboard: due today, new today, streak, quick "Start studying"
- Stats: reviews over time, retention %, upcoming due forecast, kanji learned by JLPT
- **Exit check:** numbers reconcile with `review_log`

### Phase 5 — Polish (week 6–7)
- Settings screen (per-deck limits, theme, FSRS params, font)
- Credits/licenses screen
- Keyboard shortcuts (space = reveal, 1–4 = rate)
- Light/dark theme, bundled Noto Sans JP
- `README.md`: `uv sync` then `uv run kanji-app` — one-command setup for you and your friend
- First-run: copy the bundled `resources/kanji.db` to a per-user data dir so study data survives updates
- **Exit check:** fresh `git clone` → `uv sync` → `uv run kanji-app` works on a clean machine
- **This is the usable MVP:** N5 kanji, recognition + recall, one deck, full SRS loop.

### Phase 6 — Multiple decks (week 7–8)
- Deck list / create / edit / delete UI; per-deck new & review limits
- "Move/copy card to deck", deck picker when adding a kanji
- Dashboard and stats become per-deck + "all decks"
- **Exit check:** two kanji decks schedule independently; limits are per-deck

### Phase 7 — Vocabulary (week 8–10)
- Full JMdict import (or a curated JLPT-tagged subset); `VocabRepo`
- `vocab_browser_view` + `vocab_detail_view` (expression, kana, glosses, component kanji links)
- Vocab card creation; `card_widget` renders vocab prompts (word ⇄ meaning/reading)
- Example sentences from Tatoeba on the detail + review screens
- Mixed decks allowed
- **Exit check:** a vocab card and a kanji card review in the same session and schedule correctly

### Later / optional
- Frozen/standalone build (PyInstaller) — only if the audience ever grows beyond Python users
- Handwriting practice: draw on canvas, compare stroke count/order to KanjiVG (no ML needed for a basic version)
- Audio (pronunciation via bundled TTS or recorded clips)
- Import/export decks (Anki `.apkg` compatibility)
- Custom study filters, leech detection, FSRS parameter re-optimization from your own `review_log`
- Sync (only if you ever want multi-device — big scope jump)

## 7. Testing strategy

- `core/` and `services/`: pure unit tests, fast, no DB or Qt. Aim high coverage here — this is the logic Claude edits most.
- `data/`: integration tests against a temp SQLite file seeded from a fixture.
- `srs.py`: property-style tests (a correct answer never shortens the interval; lapses reduce stability).
- UI: light smoke tests with `pytest-qt` (view constructs, key signals fire). Don't over-invest.
- Add a `make check` / `scripts/check.py` that runs `ruff`, `mypy`, `pytest` — run it before every commit.

## 8. Working with Claude effectively

- **`CLAUDE.md`** at repo root stating: the dependency rule (§4), "SQL only in repositories," "no Qt in core/services," how to run tests, and where data importers live.
- Keep files **under ~200 lines**; one class/concern per file. Small files = Claude loads only what it needs.
- **Type-hint everything**; run `mypy` strict. Types give Claude guardrails.
- Work **one phase / one view at a time**; land tests with each change.
- Prefer **pure functions** in `core/` — easy for Claude to reason about and test.
- Write a short **docstring per module** explaining its role in the architecture.
- Commit small; keep a `CHANGELOG.md` or good commit messages so context is recoverable.

## 9. First concrete steps

1. Scaffold the repo per §4 with tooling configured (`uv`, `ruff`, `mypy`, `pytest`).
2. Write `CLAUDE.md` (dependency rule, "SQL only in repositories", "no Qt in core/services", generic-schema principle).
3. Define `schema.sql` with the **full** model from §5 (polymorphic cards, deck table) even though the MVP only uses part of it.
4. Build the KANJIDIC2 importer and a minimal `kanji.db` (N5 only) to develop against.
5. Get a blank PySide6 window launching, then build Phase 2 (browser) as the first visible feature.

## 10. Open questions

All resolved:
- **Content:** JLPT N5 first.
- **Card modes:** recognition + recall in the MVP.
- **Distribution:** run from source with `uv`; no packaging.

Nothing blocking — ready to scaffold Phase 0.
