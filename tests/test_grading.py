from __future__ import annotations

from kanji_app.core.grading import matches_reading, normalise_reading, rating_for
from kanji_app.core.models import Rating


def test_normalise_folds_romaji_and_katakana_to_hiragana() -> None:
    assert normalise_reading("mizu") == "みず"
    assert normalise_reading("スイ") == "すい"
    assert normalise_reading(" あか.い ") == "あかい"


def test_matches_any_accepted_reading_in_kana_or_romaji() -> None:
    accepted = ("スイ", "みず")
    assert matches_reading("sui", accepted)
    assert matches_reading("みず", accepted)
    assert not matches_reading("yama", accepted)


def test_blank_guess_or_nothing_accepted_never_matches() -> None:
    assert not matches_reading("   ", ("みず",))
    assert not matches_reading("mizu", ())


def test_auto_grades_map_to_good_or_again_only() -> None:
    assert rating_for(True) == Rating.GOOD
    assert rating_for(False) == Rating.AGAIN
