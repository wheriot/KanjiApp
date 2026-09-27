from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from kanji_app.core import kanjivg
from kanji_app.core.models import SubjectType
from kanji_app.data.repositories import KanjiRepo, MnemonicRepo
from kanji_app.services.components import ComponentInfo, format_components, resolve_components
from kanji_app.services.study import StudyService
from kanji_app.ui.app import build_app
from kanji_app.ui.view_models.catalog_vm import CatalogViewModel
from kanji_app.ui.view_models.review_vm import ReviewViewModel
from kanji_app.ui.widgets.card_widget import CardFace
from kanji_app.ui.widgets.mnemonic_editor import MnemonicEditor

NOON = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

COMPOSITE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 109 109">
<g id="kvg:StrokePaths_x" style="fill:none;">
<g id="kvg:x" kvg:element="X">
    <g id="kvg:x-g1" kvg:element="水" kvg:position="left">
        <path id="kvg:x-s1" d="M1,1"/>
    </g>
    <g id="kvg:x-g2" kvg:element="山" kvg:position="right" kvg:phon="山">
        <g id="kvg:x-g3" kvg:element="inner"><path id="kvg:x-s2" d="M2,2"/></g>
    </g>
    <g id="kvg:x-g4" kvg:element="亻" kvg:variant="true" kvg:original="一"/>
</g>
</g>
<g id="kvg:StrokeNumbers_x"><text>1</text></g>
</svg>"""


# -- core: component parsing ------------------------------------------------


def test_components_are_the_top_level_parts_only() -> None:
    parts = kanjivg.components(COMPOSITE_SVG)
    assert [p.element for p in parts] == ["水", "山"]  # 'inner' is nested, self-closing skipped
    assert [p.phonetic for p in parts] == [False, True]


def test_components_record_the_original_of_a_variant() -> None:
    svg = COMPOSITE_SVG.replace(
        '<g id="kvg:x-g4" kvg:element="亻" kvg:variant="true" kvg:original="一"/>',
        '<g id="kvg:x-g4" kvg:element="亻" kvg:original="一"><path id="p" d="M3,3"/></g>',
    )
    parts = kanjivg.components(svg)
    assert parts[-1] == kanjivg.Component("亻", "一", False)


def test_a_kanji_with_no_parts_has_no_components() -> None:
    simple = (
        '<svg><g id="kvg:StrokePaths_x"><g id="kvg:x" kvg:element="一">'
        '<path id="kvg:x-s1" d="M1,1"/></g></g></svg>'
    )
    assert kanjivg.components(simple) == ()


# -- services: naming the parts ---------------------------------------------


def test_resolve_names_parts_from_the_dictionary(kanji_db: sqlite3.Connection) -> None:
    parts = resolve_components(KanjiRepo(kanji_db), COMPOSITE_SVG, "X")
    assert parts == [ComponentInfo("水", "water", False), ComponentInfo("山", "mountain", True)]
    assert format_components(parts) == "水 water + 山 mountain (sound)"


def test_resolve_skips_the_kanji_itself_and_handles_missing_svg(
    kanji_db: sqlite3.Connection,
) -> None:
    repo = KanjiRepo(kanji_db)
    assert resolve_components(repo, None, "水") == []
    assert [p.element for p in resolve_components(repo, COMPOSITE_SVG, "水")] == ["山"]


def test_format_components_leaves_unnamed_parts_bare() -> None:
    assert format_components([ComponentInfo("龶", "", False)]) == "龶"


# -- data + service: the learner's note -------------------------------------


def test_mnemonic_repo_roundtrip_update_and_blank_removes(conn: sqlite3.Connection) -> None:
    repo = MnemonicRepo(conn)
    assert repo.get(SubjectType.KANJI, 5) == ""

    repo.set(SubjectType.KANJI, 5, "  a tree beside a person rests  ")
    assert repo.get(SubjectType.KANJI, 5) == "a tree beside a person rests"
    assert repo.get(SubjectType.VOCAB, 5) == ""  # keyed by subject type too

    repo.set(SubjectType.KANJI, 5, "updated")
    assert repo.get(SubjectType.KANJI, 5) == "updated"

    repo.set(SubjectType.KANJI, 5, "   ")
    assert repo.get(SubjectType.KANJI, 5) == ""


def test_review_items_carry_the_note_and_the_kanji_parts(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    ming = reference_repo.get_by_literal("明")
    assert ming is not None
    deck = study_service.default_deck()
    study_service.add_kanji(deck.id, ming.id, NOON)
    study_service.set_mnemonic(SubjectType.KANJI, ming.id, "sun and moon = bright")

    items = study_service.start_session(deck.id, NOON)
    assert items
    for item in items:
        assert item.mnemonic == "sun and moon = bright"
        assert "日" in item.components and "月" in item.components


def test_review_vm_edit_updates_every_queued_card_of_the_subject(
    study_service: StudyService,
) -> None:
    deck = study_service.default_deck()
    study_service.add_kanji(deck.id, 1, NOON)
    vm = ReviewViewModel(study_service, deck.id)
    vm.start(NOON)
    assert all(item.mnemonic == "" for item in vm._queue)

    vm.set_mnemonic("  my story  ")
    assert all(item.mnemonic == "my story" for item in vm._queue)
    assert study_service.mnemonic(SubjectType.KANJI, 1) == "my story"


# -- ui ---------------------------------------------------------------------


def test_card_face_shows_parts_and_note_only_after_reveal(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    build_app([])
    ming = reference_repo.get_by_literal("明")
    assert ming is not None
    deck = study_service.default_deck()
    study_service.add_kanji(deck.id, ming.id, NOON)
    study_service.set_mnemonic(SubjectType.KANJI, ming.id, "bright")
    item = study_service.start_session(deck.id, NOON)[0]

    face = CardFace()
    face.show_item(item, revealed=False)
    assert face._memory.isHidden()

    face.show_item(item, revealed=True)
    assert not face._memory.isHidden()
    assert "bright" in face._memory.text()
    assert "Parts:" in face._memory.text()


def test_mnemonic_editor_saves_only_when_changed() -> None:
    build_app([])
    editor = MnemonicEditor()
    saved: list[str] = []
    editor.saved.connect(saved.append)

    editor.set_text("old")
    assert not editor._save.isEnabled()

    editor._edit.setPlainText("new note ")
    assert editor._save.isEnabled()
    editor._save.click()
    assert saved == ["new note"]
    assert not editor._save.isEnabled()

    editor.set_editable(False)
    editor._edit.setPlainText("blocked")
    assert not editor._save.isEnabled()


def test_catalog_vm_saves_and_reloads_the_selected_kanji_note(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    from kanji_app.services.catalog import open_bundled_catalog

    catalog = open_bundled_catalog()
    try:
        ming = reference_repo.get_by_literal("明")
        assert ming is not None
        vm = CatalogViewModel(catalog, study_service, study_service.default_deck().id)
        vm.select(ming.id)

        assert vm.selected_mnemonic() == ""
        assert "日" in vm.selected_parts()
        vm.save_mnemonic("sun + moon")
        assert vm.selected_mnemonic() == "sun + moon"
    finally:
        catalog.close()
