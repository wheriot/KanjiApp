from __future__ import annotations

from kanji_app.core import kanjivg

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" "x" []>
<svg xmlns="http://www.w3.org/2000/svg" width="109" height="109" viewBox="0 0 109 109">
<g id="kvg:StrokePaths_06c34" style="stroke:#000000;stroke-width:3;">
<g id="kvg:06c34" kvg:element="水">
    <path id="kvg:06c34-s1" kvg:type="a" d="M52,15c1,1 2,3 2,5"/>
    <path id="kvg:06c34-s2" kvg:type="b" d="M17,45c1,0 3,0 5,0"/>
    <path id="kvg:06c34-s3" kvg:type="c" d="M81,27c0,1 -1,2 -1,3"/>
    <path id="kvg:06c34-s4" kvg:type="d" d="M57,46c8,10 19,21 28,27"/>
</g>
</g>
<g id="kvg:StrokeNumbers_06c34" style="font-size:8"><text>1</text></g>
</svg>
"""


def test_parse_extracts_ordered_strokes() -> None:
    drawing = kanjivg.parse(SAMPLE)
    assert drawing.stroke_count == 4
    assert drawing.view_box == "0 0 109 109"
    assert drawing.strokes[0] == "M52,15c1,1 2,3 2,5"
    assert drawing.strokes[-1].startswith("M57,46")


def test_parse_ignores_stroke_number_text() -> None:
    # the <text>1</text> in StrokeNumbers must not be mistaken for a stroke
    assert kanjivg.parse(SAMPLE).stroke_count == 4


def test_render_full_shows_every_stroke_in_ink() -> None:
    svg = kanjivg.render(kanjivg.parse(SAMPLE), upto=None, ink="#111111")
    assert svg.count("<path") == 4
    assert "#111111" in svg
    assert "stroke-opacity" not in svg


def test_render_partial_highlights_current_and_fades_future() -> None:
    drawing = kanjivg.parse(SAMPLE)
    svg = kanjivg.render(drawing, upto=2, ink="#111111", accent="#ff0000")
    assert svg.count("<path") == 4  # 1 ink + 1 accent + 2 faded
    assert svg.count("#ff0000") == 1
    assert svg.count('stroke-opacity="0.15"') == 2


def test_render_partial_can_omit_future() -> None:
    svg = kanjivg.render(kanjivg.parse(SAMPLE), upto=2, show_future=False)
    assert svg.count("<path") == 2


def test_parse_empty_svg_is_safe() -> None:
    drawing = kanjivg.parse("<svg></svg>")
    assert drawing.stroke_count == 0
    assert kanjivg.render(drawing).count("<path") == 0
