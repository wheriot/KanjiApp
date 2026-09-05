"""Smoke tests for the Dashboard and Stats screens and their view-models."""

from __future__ import annotations

from kanji_app.core.models import Rating
from kanji_app.services.study import StudyService
from kanji_app.ui.app import build_app
from kanji_app.ui.view_models.dashboard_vm import DashboardViewModel
from kanji_app.ui.view_models.stats_vm import StatsViewModel
from kanji_app.ui.views.dashboard_view import DashboardView
from kanji_app.ui.views.stats_view import StatsView
from kanji_app.ui.widgets.bar_chart import Bar, BarChart


def _seed(study: StudyService, kanji: int) -> int:
    deck = study.default_deck()
    for kid in range(1, kanji + 1):
        study.add_kanji(deck.id, kid)
    return deck.id


def test_dashboard_vm_reflects_deck_state(study_service: StudyService) -> None:
    deck_id = _seed(study_service, 2)
    vm = DashboardViewModel(study_service, study_service.stats_service(), deck_id)
    assert vm.new_available == 4  # 2 kanji x 2 cards, under the daily limit
    assert vm.reviewed_today == 0
    assert vm.has_work


def test_dashboard_view_start_button(study_service: StudyService) -> None:
    build_app([])
    deck_id = _seed(study_service, 1)
    view = DashboardView(DashboardViewModel(study_service, study_service.stats_service(), deck_id))

    fired: list[bool] = []
    view.study_requested.connect(lambda: fired.append(True))
    view._start.click()
    assert fired == [True]


def test_dashboard_view_idle_when_empty(study_service: StudyService) -> None:
    build_app([])
    deck_id = study_service.default_deck().id
    view = DashboardView(DashboardViewModel(study_service, study_service.stats_service(), deck_id))
    assert not view._start.isEnabled()


def test_stats_view_renders_after_reviews(study_service: StudyService) -> None:
    build_app([])
    deck_id = _seed(study_service, 3)
    for item in study_service.start_session(deck_id):
        study_service.answer(item.card, Rating.GOOD)

    view = StatsView(StatsViewModel(study_service.stats_service(), deck_id))
    assert "cards" in view._headline.text()
    assert view._jlpt_box.count() == 1  # one N-level row
    view.refresh()  # no crash on repeat


def test_bar_chart_accepts_bars() -> None:
    build_app([])
    chart = BarChart()
    chart.set_bars([Bar("M", 3), Bar("T", 0), Bar("W", 5)])
    chart.resize(200, 120)
    chart.grab()  # force a paint
