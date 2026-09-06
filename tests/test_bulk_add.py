from __future__ import annotations

from datetime import UTC, datetime

from kanji_app.data.repositories import KanjiRepo
from kanji_app.services.catalog import open_bundled_catalog
from kanji_app.services.study import StudyService
from kanji_app.ui.view_models.catalog_vm import CatalogViewModel

NOON = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def test_add_kanji_bulk_is_transactional_and_idempotent(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    deck = study_service.default_deck()
    n5_ids = [k.id for k in reference_repo.find(jlpt=5)]

    added = study_service.add_kanji_bulk(deck.id, n5_ids, NOON)
    assert added == len(n5_ids) * 2  # recognition + recall each
    assert study_service.deck_card_count(deck.id) == len(n5_ids) * 2

    # re-adding the same set plus one more only creates the new one
    extra = reference_repo.find(jlpt=4)[0].id
    assert study_service.add_kanji_bulk(deck.id, [*n5_ids, extra], NOON) == 2


def test_catalog_vm_add_all_respects_the_current_filter(study_service: StudyService) -> None:
    catalog = open_bundled_catalog()
    try:
        deck_id = study_service.default_deck().id
        vm = CatalogViewModel(catalog, study_service, deck_id)
        vm.set_grade(1)  # 80 grade-1 kanji

        pending_before = vm.not_in_deck_count()
        assert pending_before == len(vm.results) == 80

        events: list[bool] = []
        vm.deck_changed.connect(lambda: events.append(True))
        added = vm.add_all_results_to_deck()

        assert added == 80
        assert events == [True]
        assert vm.not_in_deck_count() == 0
        assert study_service.deck_card_count(deck_id) == 160

        # a different filter is unaffected
        vm.set_grade(2)
        assert vm.not_in_deck_count() == len(vm.results) > 0
    finally:
        catalog.close()


def test_add_all_with_nothing_pending_returns_zero(study_service: StudyService) -> None:
    catalog = open_bundled_catalog()
    try:
        vm = CatalogViewModel(catalog, study_service, study_service.default_deck().id)
        vm.set_text("no such kanji zzz")
        assert vm.results == []
        assert vm.add_all_results_to_deck() == 0
    finally:
        catalog.close()


def test_add_all_noop_without_a_deck() -> None:
    catalog = open_bundled_catalog()
    try:
        vm = CatalogViewModel(catalog)  # no study service
        assert vm.not_in_deck_count() == 0
        assert vm.add_all_results_to_deck() == 0
        assert vm.add_top_n_to_deck(10) == 0
    finally:
        catalog.close()


def test_smart_add_takes_the_most_common_first(study_service: StudyService) -> None:
    catalog = open_bundled_catalog()
    try:
        deck_id = study_service.default_deck().id
        vm = CatalogViewModel(catalog, study_service, deck_id)  # no filter -> freq order

        added = vm.add_top_n_to_deck(15)
        assert added == 15
        assert study_service.deck_card_count(deck_id) == 30

        # the added kanji are the 15 most frequent (results are frequency-ordered)
        wanted = [k.literal for k in vm.results[:15]]
        for literal in wanted:
            assert study_service.is_in_deck(
                deck_id, next(k.id for k in vm.results if k.literal == literal)
            )

        # asking again adds the *next* 15, not the same ones
        assert vm.add_top_n_to_deck(15) == 15
    finally:
        catalog.close()
