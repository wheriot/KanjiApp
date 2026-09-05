from __future__ import annotations

from kanji_app.core.models import (
    CardMode,
    Kanji,
    Meaning,
    Reading,
    ReadingType,
)


def _mizu() -> Kanji:
    return Kanji(
        id=1,
        literal="水",
        stroke_count=4,
        jlpt=5,
        meanings=(Meaning("water"),),
        readings=(
            Reading(ReadingType.ON, "スイ"),
            Reading(ReadingType.KUN, "みず"),
        ),
    )


def test_readings_of_filters_by_type() -> None:
    k = _mizu()
    assert k.readings_of(ReadingType.ON) == ("スイ",)
    assert k.readings_of(ReadingType.KUN) == ("みず",)
    assert k.readings_of(ReadingType.NANORI) == ()


def test_enums_are_strings() -> None:
    assert CardMode.RECOGNITION.value == "recognition"
    assert str(ReadingType.KUN) == "kun"
    assert ReadingType("kun") is ReadingType.KUN
