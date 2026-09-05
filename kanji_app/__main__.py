"""Entry point: ``python -m kanji_app`` / ``uv run kanji-app``."""

from __future__ import annotations

import sys


def main() -> int:
    from kanji_app.ui.app import run

    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
