"""Kanji App — a desktop spaced-repetition app for learning Japanese kanji.

Architecture (see CLAUDE.md for the rules):

    ui  ->  ui.view_models  ->  services  ->  core / data

- ``core``      pure domain logic, no Qt, no SQL
- ``data``      SQLite access; all SQL lives in ``data.repositories``
- ``services``  use-cases that wire ``core`` + ``data`` together, no Qt
- ``ui``        PySide6 widgets and view-models
"""

__version__ = "0.1.0"
