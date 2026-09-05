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

## Japanese fonts (optional)

The app uses your OS's Japanese fonts by default (fine on Windows/macOS). To
bundle Noto Sans JP for identical rendering everywhere:

```
uv run python -m scripts.fetch_font
```

## Data pipeline

The shipped reference database `kanji_app/resources/kanji.db` is built from
KANJIDIC2, KanjiVG and JMdict, scoped to a charset file
(`kanji_app/resources/jlpt/n5.txt`):

```
uv run python -m scripts.build_db          # downloads + caches sources, builds N5 db
```

Widen coverage by adding e.g. `kanji_app/resources/jlpt/n4.txt` and rerunning with
`--charset ... --jlpt 4`. Individual importers: `scripts.import_kanjidic`,
`scripts.import_kanjivg`, `scripts.import_jmdict`. Pass `--no-vocab` to skip JMdict.

## Project status

Phases 0–7 complete. Dashboard, Browse (kanji + vocabulary), Review (recognition
+ recall, FSRS), multiple Decks, Stats, and Settings. Ships 103 N5 kanji with
stroke order and ~1080 N5 vocabulary entries. See [PLAN.md](PLAN.md).

## Data & licenses

- **KANJIDIC2**, **JMdict** — © EDRDG, CC BY-SA 4.0
- **KanjiVG** — © Ulrich Apel / KanjiVG, CC BY-SA 3.0
- **Noto Sans JP** (optional, fetched on demand) — SIL Open Font License 1.1

Attribution is required; the app will ship a Credits screen. See
[PLAN.md](PLAN.md) § "Data sources".
