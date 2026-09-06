from __future__ import annotations

from datetime import UTC, datetime

from kanji_app.core.romaji import to_romaji
from kanji_app.data.repositories import KanjiRepo
from kanji_app.services.settings import AppSettings
from kanji_app.services.study import StudyService
from kanji_app.ui.view_models.review_vm import ReviewViewModel

NOON = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _deck_with_kanji(study: StudyService, repo: KanjiRepo, n: int) -> int:
    deck_id = study.default_deck().id
    for kid in [k.id for k in repo.find(jlpt=5)[:n]]:
        study.add_kanji(deck_id, kid, NOON)
    return deck_id


def test_choose_mode_builds_four_options_including_the_answer(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    study_service.update_settings(AppSettings(review_input="choose"))
    deck_id = _deck_with_kanji(study_service, reference_repo, 3)

    vm = ReviewViewModel(study_service, deck_id)
    vm.start(NOON)
    item = vm.current
    assert item is not None
    assert len(item.options) == 4
    assert item.options[item.correct_option] == item.answer


def test_choose_mode_grades_and_advances(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    study_service.update_settings(AppSettings(review_input="choose"))
    deck_id = _deck_with_kanji(study_service, reference_repo, 2)
    vm = ReviewViewModel(study_service, deck_id)
    vm.start(NOON)

    item = vm.current
    assert item is not None
    vm.choose(item.correct_option)
    assert vm.graded_correct is True
    assert vm.revealed

    vm.continue_()
    assert vm.answered == 1
    assert vm.graded_correct is None

    nxt = vm.current
    assert nxt is not None
    vm.choose((nxt.correct_option + 1) % 4)
    assert vm.graded_correct is False


def test_type_mode_hides_reading_and_checks_romaji_or_kana(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    study_service.update_settings(AppSettings(review_input="type"))
    deck_id = _deck_with_kanji(study_service, reference_repo, 2)
    vm = ReviewViewModel(study_service, deck_id)
    vm.start(NOON)

    item = vm.current
    assert item is not None
    assert item.prompt_note == ""  # the reading is not shown
    assert item.accepted

    vm.submit_reading(to_romaji(item.accepted[0]))  # romaji accepted
    assert vm.graded_correct is True
    vm.continue_()

    nxt = vm.current
    assert nxt is not None
    vm.submit_reading(nxt.accepted[0])  # exact kana accepted
    assert vm.graded_correct is True


def test_type_mode_rejects_a_wrong_reading(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    study_service.update_settings(AppSettings(review_input="type"))
    deck_id = _deck_with_kanji(study_service, reference_repo, 1)
    vm = ReviewViewModel(study_service, deck_id)
    vm.start(NOON)

    vm.submit_reading("ばか")
    assert vm.graded_correct is False
    vm.submit_reading("")  # empty is not a free pass
    # still on the same card, still wrong-marked
    assert vm.graded_correct is False


def test_default_reveal_mode_is_unchanged(
    study_service: StudyService, reference_repo: KanjiRepo
) -> None:
    deck_id = _deck_with_kanji(study_service, reference_repo, 1)
    vm = ReviewViewModel(study_service, deck_id)
    assert vm.input_mode == "reveal"
    vm.start(NOON)
    item = vm.current
    assert item is not None and item.options == () and item.accepted == ()
