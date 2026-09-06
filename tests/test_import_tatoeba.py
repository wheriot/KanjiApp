from __future__ import annotations

import sqlite3
from pathlib import Path

from kanji_app.data.repositories import VocabRepo
from scripts.import_tatoeba import import_tatoeba

SAMPLE = """A: 水を飲む。\tI drink water.#ID=1_1
B: 水(みず) を 飲む(のむ)
A: 彼は水泳がとても好きで、時間さえあれば毎日プールに通っている。\tHe likes swimming a lot.#ID=2_2
B: 彼(かれ) は 水泳(すいえい) が とても 好き(すき) で 時間(じかん) さえ 通う(かよう)
A: 山に登る。\tClimb the mountain.#ID=3_3
B: 山(やま) に 登る(のぼる)
"""


def test_import_links_short_sentences_and_skips_long_ones(
    kanji_db: sqlite3.Connection, tmp_path: Path
) -> None:
    kanji_db.executescript(
        """
        INSERT INTO vocab (id, expression, kana) VALUES
            (1, '水', 'みず'), (2, '水泳', 'すいえい'), (3, '山', 'やま');
        INSERT INTO vocab_gloss (vocab_id, value) VALUES (1,'water'),(2,'swimming'),(3,'mountain');
        """
    )
    src = tmp_path / "examples.utf"
    src.write_text(SAMPLE, encoding="utf-8")

    sentences, links = import_tatoeba(src, kanji_db, {"水", "山", "泳", "飲", "登"})
    assert sentences == 2  # the long 水泳 sentence is dropped for length
    assert links == 2

    repo = VocabRepo(kanji_db)
    mizu = repo.sentences_for(1)
    assert len(mizu) == 1
    assert mizu[0].japanese == "水を飲む。"
    assert mizu[0].english == "I drink water."
    assert repo.sentences_for(2) == []  # 水泳 had only the over-length sentence
