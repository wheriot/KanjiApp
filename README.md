# Kanji App

A desktop spaced-repetition app for learning Japanese kanji, built with Python + PySide6.

See [PLAN.md](PLAN.md) for the full design and roadmap, and [CLAUDE.md](CLAUDE.md) for
architecture rules.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```
uv sync
```

## Run

```
uv run kanji-app
```

## Develop

```
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Or all at once:

```
uv run python scripts/check.py
```

## Data pipeline

The shipped reference database `kanji_app/resources/kanji.db` is built from
KANJIDIC2 and KanjiVG, scoped to a charset file (`kanji_app/resources/jlpt/n5.txt`):

```
uv run python -m scripts.build_db          # downloads + caches sources, builds N5 db
```

Widen coverage by adding e.g. `kanji_app/resources/jlpt/n4.txt` and rerunning with
`--charset ... --jlpt 4`. Individual importers: `scripts.import_kanjidic`,
`scripts.import_kanjivg`.

## Project status

Phase 2 — kanji browser. `uv run kanji-app` opens the Browse screen: search/filter
the 103 N5 kanji, inspect readings + meanings, and watch stroke order animate.
See [PLAN.md](PLAN.md) § "Feature roadmap".

## Data & licenses

- **KANJIDIC2** — © EDRDG, CC BY-SA 4.0
- **KanjiVG** — © Ulrich Apel / KanjiVG, CC BY-SA 3.0
- JMdict / Tatoeba will be added with vocabulary support (Phase 7)

Attribution is required; the app will ship a Credits screen. See
[PLAN.md](PLAN.md) § "Data sources".
