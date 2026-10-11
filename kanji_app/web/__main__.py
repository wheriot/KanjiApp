"""Entry point: ``uv run kanji-web`` — serve phone reviews from this computer."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Kanji App review page for a phone.")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="interface to listen on (default: this PC only, for `tailscale serve`)",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="study data folder (default: the desktop app's, so progress is shared)",
    )
    args = parser.parse_args()

    try:
        import uvicorn

        from kanji_app.web.app import create_app
    except ImportError:
        print("The web extra isn't installed. Run:  uv sync --extra web")
        return 1

    from kanji_app.services.study import open_study_service

    study = open_study_service(args.data_dir, check_same_thread=False)
    try:
        uvicorn.run(create_app(study), host=args.host, port=args.port)
    finally:
        study.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
