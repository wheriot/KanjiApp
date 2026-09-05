from __future__ import annotations

from kanji_app.core.models import Rating
from kanji_app.services.study import StudyService
from kanji_app.ui.view_models.review_vm import ReviewViewModel


def _vm_with_cards(study: StudyService, kanji_count: int) -> ReviewViewModel:
    deck = study.default_deck()
    for kid in range(1, kanji_count + 1):
        study.add_kanji(deck.id, kid)
    return ReviewViewModel(study, deck.id)


def test_start_populates_queue(study_service: StudyService) -> None:
    vm = _vm_with_cards(study_service, 2)  # 4 cards
    assert vm.current is None
    vm.start()
    assert vm.current is not None
    assert vm.remaining == 4
    assert not vm.revealed


def test_reveal_then_answer_advances(study_service: StudyService) -> None:
    vm = _vm_with_cards(study_service, 1)  # 2 cards
    vm.start()
    first = vm.current

    vm.answer(Rating.GOOD)  # ignored: not revealed yet
    assert vm.current is first

    vm.reveal()
    assert vm.revealed
    vm.answer(Rating.GOOD)
    assert vm.answered == 1
    assert vm.current is not first
    assert not vm.revealed


def test_session_finishes(study_service: StudyService) -> None:
    vm = _vm_with_cards(study_service, 1)
    events: list[int] = []
    vm.state_changed.connect(lambda: events.append(vm.remaining))
    vm.start()
    for _ in range(2):
        vm.reveal()
        vm.answer(Rating.GOOD)
    assert vm.current is None
    assert vm.in_progress is False
    assert vm.pending_counts().total == 0
