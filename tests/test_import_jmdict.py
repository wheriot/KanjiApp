from __future__ import annotations

import sqlite3
from pathlib import Path

from kanji_app.data.repositories import VocabRepo
from scripts.import_jmdict import import_jmdict

SAMPLE = """<?xml version="1.0"?>
<JMdict>
  <entry>
    <ent_seq>1</ent_seq>
    <k_ele><keb>水</keb><ke_pri>ichi1</ke_pri></k_ele>
    <r_ele><reb>みず</reb></r_ele>
    <sense><gloss xml:lang="eng">water</gloss></sense>
  </entry>
  <entry>
    <ent_seq>2</ent_seq>
    <k_ele><keb>山川</keb><ke_pri>news1</ke_pri></k_ele>
    <r_ele><reb>やまかわ</reb></r_ele>
    <sense><gloss xml:lang="eng">mountains and rivers</gloss></sense>
  </entry>
  <entry>
    <ent_seq>3</ent_seq>
    <k_ele><keb>裏</keb><ke_pri>ichi1</ke_pri></k_ele>
    <r_ele><reb>うら</reb></r_ele>
    <sense><gloss xml:lang="eng">back (not in charset)</gloss></sense>
  </entry>
  <entry>
    <ent_seq>4</ent_seq>
    <k_ele><keb>水</keb></k_ele>
    <r_ele><reb>みず</reb></r_ele>
    <sense><gloss xml:lang="eng">not common, no ke_pri</gloss></sense>
  </entry>
</JMdict>
"""


def test_import_filters_to_charset_and_common_words(
    kanji_db: sqlite3.Connection, tmp_path: Path
) -> None:
    src = tmp_path / "JMdict_e"
    src.write_text(SAMPLE, encoding="utf-8")

    count = import_jmdict(src, kanji_db, charset={"水", "山"})
    assert count == 1  # only 水 qualifies: 山川 needs 川 (not in this charset),
    #                     裏 not in charset, entry 4 has no ke_pri

    repo = VocabRepo(kanji_db)
    (word,) = repo.find()
    assert word.expression == "水"
    assert word.glosses == ("water",)
    assert word.kanji_ids == (1,)  # linked to kanji 水 (id 1 in the fixture)


def test_reimport_replaces_vocab(kanji_db: sqlite3.Connection, tmp_path: Path) -> None:
    src = tmp_path / "JMdict_e"
    src.write_text(SAMPLE, encoding="utf-8")
    import_jmdict(src, kanji_db, charset={"水", "山", "川"})
    import_jmdict(src, kanji_db, charset={"水", "山", "川"})
    assert VocabRepo(kanji_db).count() == 2  # 水 + 山川, not doubled
