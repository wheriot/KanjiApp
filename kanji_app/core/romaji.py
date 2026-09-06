"""Kana <-> romaji conversion, for pronunciation hints and typed-answer checking.

``to_romaji`` produces modified Hepburn (long vowels as macrons, ``n`` kept
before b/p/m). ``to_kana`` is forgiving: it accepts Hepburn *and* kunrei spellings
(shi/si, tsu/tu, fu/hu, ji/zi, ...) so a learner can type a reading without an IME.
"""

from __future__ import annotations

_BASE: dict[str, str] = {
    "あ": "a",
    "い": "i",
    "う": "u",
    "え": "e",
    "お": "o",
    "か": "ka",
    "き": "ki",
    "く": "ku",
    "け": "ke",
    "こ": "ko",
    "が": "ga",
    "ぎ": "gi",
    "ぐ": "gu",
    "げ": "ge",
    "ご": "go",
    "さ": "sa",
    "し": "shi",
    "す": "su",
    "せ": "se",
    "そ": "so",
    "ざ": "za",
    "じ": "ji",
    "ず": "zu",
    "ぜ": "ze",
    "ぞ": "zo",
    "た": "ta",
    "ち": "chi",
    "つ": "tsu",
    "て": "te",
    "と": "to",
    "だ": "da",
    "ぢ": "ji",
    "づ": "zu",
    "で": "de",
    "ど": "do",
    "な": "na",
    "に": "ni",
    "ぬ": "nu",
    "ね": "ne",
    "の": "no",
    "は": "ha",
    "ひ": "hi",
    "ふ": "fu",
    "へ": "he",
    "ほ": "ho",
    "ば": "ba",
    "び": "bi",
    "ぶ": "bu",
    "べ": "be",
    "ぼ": "bo",
    "ぱ": "pa",
    "ぴ": "pi",
    "ぷ": "pu",
    "ぺ": "pe",
    "ぽ": "po",
    "ま": "ma",
    "み": "mi",
    "む": "mu",
    "め": "me",
    "も": "mo",
    "や": "ya",
    "ゆ": "yu",
    "よ": "yo",
    "ら": "ra",
    "り": "ri",
    "る": "ru",
    "れ": "re",
    "ろ": "ro",
    "わ": "wa",
    "ゐ": "wi",
    "ゑ": "we",
    "を": "o",
    "ん": "n",
    "ー": "-",
}
_YOON: dict[str, str] = {
    "きゃ": "kya",
    "きゅ": "kyu",
    "きょ": "kyo",
    "ぎゃ": "gya",
    "ぎゅ": "gyu",
    "ぎょ": "gyo",
    "しゃ": "sha",
    "しゅ": "shu",
    "しょ": "sho",
    "じゃ": "ja",
    "じゅ": "ju",
    "じょ": "jo",
    "ちゃ": "cha",
    "ちゅ": "chu",
    "ちょ": "cho",
    "にゃ": "nya",
    "にゅ": "nyu",
    "にょ": "nyo",
    "ひゃ": "hya",
    "ひゅ": "hyu",
    "ひょ": "hyo",
    "びゃ": "bya",
    "びゅ": "byu",
    "びょ": "byo",
    "ぴゃ": "pya",
    "ぴゅ": "pyu",
    "ぴょ": "pyo",
    "みゃ": "mya",
    "みゅ": "myu",
    "みょ": "myo",
    "りゃ": "rya",
    "りゅ": "ryu",
    "りょ": "ryo",
}
_MACRON = {"a": "ā", "i": "ī", "u": "ū", "e": "ē", "o": "ō"}
_SMALL_KANA = "ぁぃぅぇぉゃゅょゎ"


def _to_hiragana(text: str) -> str:
    """Fold katakana onto hiragana so one table covers both scripts."""
    out = []
    for ch in text:
        code = ord(ch)
        out.append(chr(code - 0x60) if 0x30A1 <= code <= 0x30F6 else ch)
    return "".join(out)


def to_romaji(kana: str) -> str:
    src = _to_hiragana(kana)
    syllables: list[str] = []
    i = 0
    while i < len(src):
        pair = src[i : i + 2]
        if pair in _YOON:
            syllables.append(_YOON[pair])
            i += 2
        elif src[i] == "っ":
            nxt = _peek_romaji(src, i + 1)
            syllables.append(nxt[0] if nxt else "")
            i += 1
        elif src[i] in _BASE:
            syllables.append(_BASE[src[i]])
            i += 1
        else:
            syllables.append(src[i])
            i += 1
    return _apply_long_vowels("".join(syllables))


def _peek_romaji(src: str, index: int) -> str:
    if index >= len(src):
        return ""
    pair = src[index : index + 2]
    if pair in _YOON:
        return _YOON[pair]
    return _BASE.get(src[index], "")


def _apply_long_vowels(romaji: str) -> str:
    out: list[str] = []
    for ch in romaji:
        prev = out[-1] if out else ""
        if ch == "-":
            if prev in _MACRON:
                out[-1] = _MACRON[prev]
            continue
        if ch in "uo" and prev == ch:  # ou/oo/uu -> long vowel
            out[-1] = _MACRON[ch]
            continue
        out.append(ch)
    return "".join(out)


# -- romaji -> kana --------------------------------------------------

_ROMAJI_TO_KANA: dict[str, str] = {}
for _kana, _rom in {**_BASE, **_YOON}.items():
    _ROMAJI_TO_KANA.setdefault(_rom, _kana)
_ROMAJI_TO_KANA.update(
    {
        "si": "し",
        "ti": "ち",
        "tu": "つ",
        "hu": "ふ",
        "zi": "じ",
        "di": "ぢ",
        "du": "づ",
        "sya": "しゃ",
        "syu": "しゅ",
        "syo": "しょ",
        "tya": "ちゃ",
        "tyu": "ちゅ",
        "tyo": "ちょ",
        "zya": "じゃ",
        "zyu": "じゅ",
        "zyo": "じょ",
        "jya": "じゃ",
        "jyu": "じゅ",
        "jyo": "じょ",
        "cya": "ちゃ",
        "cyu": "ちゅ",
        "cyo": "ちょ",
        "wo": "を",
        "n'": "ん",
        "nn": "ん",
    }
)
_MAX_ROMAJI_KEY = max(len(k) for k in _ROMAJI_TO_KANA)


def to_kana(romaji: str) -> str:
    src = romaji.strip().lower()
    for macron, plain in [("ā", "aa"), ("ī", "ii"), ("ū", "uu"), ("ē", "ee"), ("ō", "oo")]:
        src = src.replace(macron, plain)
    out: list[str] = []
    i = 0
    while i < len(src):
        if src[i] == "-":
            out.append("ー")
            i += 1
            continue
        # double consonant (not "nn") -> っ
        if src[i] not in "aiueon-" and i + 1 < len(src) and src[i + 1] == src[i]:
            out.append("っ")
            i += 1
            continue
        matched = False
        for size in range(min(_MAX_ROMAJI_KEY, len(src) - i), 0, -1):
            chunk = src[i : i + size]
            if chunk in _ROMAJI_TO_KANA:
                out.append(_ROMAJI_TO_KANA[chunk])
                i += size
                matched = True
                break
        if not matched:
            if src[i] == "n":
                out.append("ん")
            else:
                out.append(src[i])
            i += 1
    return "".join(out)
