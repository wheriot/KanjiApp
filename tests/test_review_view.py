from __future__ import annotations

from kanji_app.core.models import Rating
from kanji_app.services.study import StudyService
from kanji_app.ui.app import build_app
from kanji_app.ui.view_models.review_vm import ReviewViewModel
from kanji_app.ui.views.review_view import ReviewView


def _view(study: StudyService, with_kanji: int = 0) -> ReviewView:
    build_app([])
    deck = study.default_deck()
    for kid in range(1, with_kanji + 1):
        study.add_kanji(deck.id, kid)
    return ReviewView(ReviewViewModel(study, deck.id))


def test_idle_state_prompts_to_add_kanji(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=0)
    assert view._footer.currentIndex() == 0
    assert "Browse" in view._idle_label.text()
    assert view._start_button.isHidden()


def test_idle_state_offers_start_when_cards_waiting(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=1)
    assert not view._start_button.isHidden()
    assert "new card" in view._idle_label.text()


def test_flow_reveal_and_rate(study_service: StudyService) -> None:
    view = _view(study_service, with_kanji=1)
    view._vm.start()
    assert view._footer.currentIndex() == 1  # "show answer"

    view._vm.reveal()
    assert view._footer.currentIndex() == 2  # rating buttons
    assert "left" in view._status.text()

    view._vm.answer(Rating.GOOD)
    assert view._vm.answered == 1
    # back to a question or the completion page
    assert view._footer.currentIndex() in (0, 1)
