"""Download a bundled Japanese UI font into ``kanji_app/assets/fonts/``.

Optional: the app falls back to the operating system's Japanese fonts when no
bundled font is present (fine on Windows and macOS). Bundling one guarantees
identical rendering everywhere, including bare Linux.

Usage:
    uv run python -m scripts.fetch_font
"""

from __future__ import annotations

import urllib.request

from scripts._common import RESOURCES

# Noto Sans JP, variable weight, subsetted — SIL Open Font License 1.1.
FONT_URL = (
    "https://raw.githubusercontent.com/notofonts/noto-cjk/main/"
    "Sans/Variable/OTF/Subset/NotoSansJP-VF.otf"
)
FONT_DIR = RESOURCES.parent / "assets" / "fonts"
FONT_PATH = FONT_DIR / "NotoSansJP-VF.otf"


def main() -> int:
    if FONT_PATH.exists():
        print(f"already present: {FONT_PATH}")
        return 0
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"downloading {FONT_URL}")
    with urllib.request.urlopen(FONT_URL) as resp:
        FONT_PATH.write_bytes(resp.read())
    print(f"saved {FONT_PATH} ({FONT_PATH.stat().st_size / 1024:.0f} KB)")
    print("Restart the app to pick it up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
