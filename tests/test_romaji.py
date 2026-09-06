from __future__ import annotations

import pytest

from kanji_app.core.romaji import to_kana, to_romaji


@pytest.mark.parametrize(
    ("kana", "expected"),
    [
        ("みず", "mizu"),
        ("やま", "yama"),
        ("がっこう", "gakkou"),
        ("きょう", "kyou"),
        ("しんぶん", "shinbun"),
        ("じしょ", "jisho"),
        ("せんせい", "sensei"),
        ("コーヒー", "kōhī"),
        ("おおきい", "ōkii"),
        ("ちゃ", "cha"),
    ],
)
def test_to_romaji(kana: str, expected: str) -> None:
    assert to_romaji(kana) == expected


@pytest.mark.parametrize(
    ("romaji", "expected"),
    [
        ("nihongo", "にほんご"),
        ("toukyou", "とうきょう"),
        ("gakkou", "がっこう"),
        ("kyou", "きょう"),
        ("shinbun", "しんぶん"),
        ("sensei", "せんせい"),
        ("jisho", "じしょ"),
        ("si", "し"),  # kunrei accepted
        ("tu", "つ"),
        ("hujin", "ふじん"),
    ],
)
def test_to_kana_accepts_hepburn_and_kunrei(romaji: str, expected: str) -> None:
    assert to_kana(romaji) == expected


def test_to_kana_of_to_romaji_is_phonetically_stable() -> None:
    for word in ["みず", "がっこう", "しんぶん", "きょう", "じてんしゃ"]:
        # round-trip: kana -> romaji -> kana should give the same reading back
        assert to_kana(to_romaji(word)) == word
