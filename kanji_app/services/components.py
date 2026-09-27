"""Kanji components: the parts a kanji is built from, as mnemonic material.

Reads KanjiVG's element groups (via ``core.kanjivg``) and names each part using
the kanji dictionary where the part is itself a kanji (日 -> "sun").
"""

from __future__ import annotations

from dataclasses import dataclass

from kanji_app.core import kanjivg
from kanji_app.data.repositories import KanjiRepo


@dataclass(frozen=True, slots=True)
class ComponentInfo:
    element: str
    meaning: str  # empty when the part isn't a kanji we have a meaning for
    phonetic: bool


def resolve_components(repo: KanjiRepo, svg: str | None, literal: str) -> list[ComponentInfo]:
    """Top-level parts of a kanji, each with its meaning where known."""
    if not svg:
        return []
    infos: list[ComponentInfo] = []
    for part in kanjivg.components(svg):
        if part.element == literal:
            continue
        named = repo.get_by_literal(part.original or part.element)
        meaning = named.meanings[0].value if named and named.meanings else ""
        infos.append(ComponentInfo(part.element, meaning, part.phonetic))
    return infos


def format_components(parts: list[ComponentInfo]) -> str:
    """e.g. ``日 sun + 月 moon`` — ``(sound)`` marks the part hinting at the reading."""
    return " + ".join(
        " ".join(bit for bit in (p.element, p.meaning, "(sound)" if p.phonetic else "") if bit)
        for p in parts
    )
