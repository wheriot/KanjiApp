"""Application configuration and filesystem paths.

Kept tiny and dependency-free on purpose. Anything that needs to know *where*
things live on disk should import from here rather than hard-coding paths.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "KanjiApp"

# Files shipped inside the package.
PACKAGE_ROOT = Path(__file__).resolve().parent
RESOURCES_DIR = PACKAGE_ROOT / "resources"
ASSETS_DIR = PACKAGE_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

# The database that ships with the app (read-only template, built by scripts/).
BUNDLED_DB = RESOURCES_DIR / "kanji.db"


def user_data_dir() -> Path:
    """Per-user writable directory for the live study database and settings.

    On first run the bundled database is copied here so a ``git pull`` never
    clobbers the user's progress.
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_NAME


@dataclass(frozen=True, slots=True)
class Paths:
    """Resolved paths for a single run of the app."""

    data_dir: Path
    database: Path

    @classmethod
    def resolve(cls, data_dir: Path | None = None) -> Paths:
        root = data_dir or user_data_dir()
        return cls(data_dir=root, database=root / "study.db")
