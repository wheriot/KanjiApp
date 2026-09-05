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

## Project status

Phase 0 — skeleton. See [PLAN.md](PLAN.md) § "Feature roadmap".

## Data & licenses

Kanji data will be built from KANJIDIC2, KanjiVG, JMdict and Tatoeba. Each carries an
attribution requirement (CC BY-SA / EDRDG); the app will ship a Credits screen. See
[PLAN.md](PLAN.md) § "Data sources".
