"""Parse KanjiVG stroke-order SVGs and re-emit them one stroke at a time.

Pure string/XML work — no Qt. The UI widget (``ui/widgets/stroke_order_widget``)
feeds the output of :func:`render` to a renderer.

KanjiVG documents put every stroke as a ``<path>`` (in drawing order) inside a
single ``kvg:StrokePaths`` group with no per-stroke transforms, so flattening
them into a fresh minimal SVG is safe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')
_STROKE_PATHS_RE = re.compile(
    r'<g id="kvg:StrokePaths.*?>(.*?)</g>\s*(?:<g id="kvg:StrokeNumbers|</svg>)',
    re.DOTALL,
)
_PATH_D_RE = re.compile(r"<path[^>]*\sd=\"([^\"]+)\"")
_GROUP_TAG_RE = re.compile(r"<g\b([^>]*)>|</g>")
_KVG_ATTR_RE = re.compile(r'kvg:(\w+)="([^"]*)"')
_COMPONENT_DEPTH = 3  # <StrokePaths> > <kanji> > <component>

DEFAULT_VIEW_BOX = "0 0 109 109"


@dataclass(frozen=True, slots=True)
class StrokeDrawing:
    view_box: str
    strokes: tuple[str, ...]

    @property
    def stroke_count(self) -> int:
        return len(self.strokes)


@dataclass(frozen=True, slots=True)
class Component:
    """A top-level part of a kanji, e.g. 日 and 月 inside 明."""

    element: str
    original: str | None = None  # base form when ``element`` is a variant (亻 -> 人)
    phonetic: bool = False  # the part that hints at the kanji's on-reading


def components(svg: str) -> tuple[Component, ...]:
    """The kanji's top-level parts, read from KanjiVG's ``kvg:element`` groups."""
    depth = 0
    parts: list[Component] = []
    for match in _GROUP_TAG_RE.finditer(svg):
        if match.group(0) == "</g>":
            depth -= 1
            continue
        if match.group(1).rstrip().endswith("/"):
            continue
        depth += 1
        if depth != _COMPONENT_DEPTH:
            continue
        attrs = dict(_KVG_ATTR_RE.findall(match.group(1)))
        if element := attrs.get("element"):
            parts.append(Component(element, attrs.get("original"), "phon" in attrs))
    return tuple(parts)


def parse(svg: str) -> StrokeDrawing:
    """Extract the ordered stroke paths from a KanjiVG SVG document."""
    view_box_match = _VIEWBOX_RE.search(svg)
    view_box = view_box_match.group(1) if view_box_match else DEFAULT_VIEW_BOX

    body_match = _STROKE_PATHS_RE.search(svg)
    body = body_match.group(1) if body_match else svg
    strokes = tuple(_PATH_D_RE.findall(body))
    return StrokeDrawing(view_box=view_box, strokes=strokes)


def render(
    drawing: StrokeDrawing,
    upto: int | None = None,
    *,
    ink: str = "#222222",
    accent: str = "#c0392b",
    show_future: bool = True,
    stroke_width: float = 3.0,
) -> str:
    """Build a standalone SVG showing the first ``upto`` strokes.

    - strokes ``1 .. upto-1`` are drawn solid in ``ink``
    - stroke ``upto`` is drawn in ``accent`` (the one "being written")
    - later strokes are drawn faint (``show_future``) or omitted

    ``upto=None`` draws every stroke solid in ``ink`` (the static view).
    """
    total = drawing.stroke_count
    shown = total if upto is None else max(0, min(upto, total))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{drawing.view_box}">',
        f'<g fill="none" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round">',
    ]
    for index, d in enumerate(drawing.strokes, start=1):
        if index < shown or upto is None:
            parts.append(f'<path d="{d}" stroke="{ink}"/>')
        elif index == shown:
            parts.append(f'<path d="{d}" stroke="{accent}"/>')
        elif show_future:
            parts.append(f'<path d="{d}" stroke="{ink}" stroke-opacity="0.15"/>')
    parts.append("</g></svg>")
    return "".join(parts)
