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
KANJIDIC2, KanjiVG and JMdict, scoped to a **charset file**:

```
uv run python -m scripts.make_charsets     # regenerate jlpt/joyo.txt + n1/n2/n4.txt
uv run python -m scripts.build_db          # downloads + caches sources, builds the db
```

`build_db` defaults to `jlpt/joyo.txt` (all 2136 Jōyō kanji) and tags kanji from
whichever `jlpt/n{1..5}.txt` files exist (`n5.txt` is hand-curated; the rest are
approximate, derived from KANJIDIC2's legacy JLPT levels — the old data predates
N3, so there is no `n3.txt`). Narrow the build with `--charset jlpt/n5.txt`.
Individual importers: `scripts.import_kanjidic`, `scripts.import_kanjivg`,
`scripts.import_jmdict`. Pass `--no-vocab` to skip JMdict.

## Project status

Phases 0–7 complete, plus follow-ups. Dashboard, Browse (kanji + vocabulary),
Review (recognition + recall, FSRS), multiple Decks, Stats, Settings. Ships all
**2136 Jōyō kanji** with stroke order, ~15k vocabulary entries with example
sentences, and romaji pronunciation hints. Filter by school grade / JLPT level,
or "add the N most common" to a deck in one click. See [PLAN.md](PLAN.md).

## Data & licenses

- **KANJIDIC2**, **JMdict** — © EDRDG, CC BY-SA 4.0
- **KanjiVG** — © Ulrich Apel / KanjiVG, CC BY-SA 3.0
- **Noto Sans JP** (optional, fetched on demand) — SIL Open Font License 1.1

Attribution is required; the app will ship a Credits screen. See
[PLAN.md](PLAN.md) § "Data sources".
