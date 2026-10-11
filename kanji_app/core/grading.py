"""Auto-grading for the ``choose`` / ``type`` review modes. Pure functions."""

from __future__ import annotations

from kanji_app.core.models import Rating
from kanji_app.core.romaji import to_kana


def normalise_reading(text: str) -> str:
    """Fold romaji to kana and katakana to hiragana; drop long-vowel/okurigana marks."""
    folded = to_kana(text.strip())
    out = []
    for ch in folded:
        code = ord(ch)
        out.append(chr(code - 0x60) if 0x30A1 <= code <= 0x30F6 else ch)
    return "".join(c for c in out if c not in "ー・.-")


def matches_reading(text: str, accepted: tuple[str, ...]) -> bool:
    """Whether a typed reading (kana or romaji) matches any accepted reading."""
    if not text.strip() or not accepted:
        return False
    guess = normalise_reading(text)
    return any(guess == normalise_reading(a) for a in accepted)


def rating_for(correct: bool) -> Rating:
    """Auto-graded answers only ever produce Good or Again."""
    return Rating.GOOD if correct else Rating.AGAIN
