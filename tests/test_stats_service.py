from __future__ import annotations

from datetime import UTC, datetime, timedelta

from kanji_app.core.models import Rating
from kanji_app.data.repositories import KanjiRepo
from kanji_app.services.study import StudyService

NOON = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


def _study_new_on(service: StudyService, deck_id: int, day_offset: int, kanji_ids: range) -> int:
    """Add fresh kanji on a given day and answer every card that comes due.

    Adding *new* kanji each day guarantees the day has reviews regardless of how
    FSRS schedules earlier cards.
    """
    moment = NOON + timedelta(days=day_offset)
    for kid in kanji_ids:
        service.add_kanji(deck_id, kid, moment)
    answered = 0
    for item in service.start_session(deck_id, moment):
        service.answer(item.card, Rating.GOOD, moment)
        answered += 1
    return answered


def test_empty_report(study_service: StudyService) -> None:
    report = study_service.stats_service().report(study_service.default_deck().id, NOON)
    assert report.total_cards == 0
    assert report.retention is None
    assert report.streak_days == 0
    assert len(report.history) == 21
    assert all(day.count == 0 for day in report.history)


def test_history_buckets_and_reviewed_today(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    stats = study_service.stats_service()
    _study_new_on(study_service, deck.id, -2, range(1, 4))
    _study_new_on(study_service, deck.id, -1, range(4, 7))
    today_count = _study_new_on(study_service, deck.id, 0, range(7, 10))

    report = stats.report(deck.id, NOON + timedelta(hours=1))
    by_day = {d.day: d.count for d in report.history}
    assert by_day[(NOON - timedelta(days=2)).date()] == 6  # 3 new kanji x 2 cards
    assert by_day[NOON.date()] == report.reviewed_today
    assert report.reviewed_today >= today_count


def test_streak_counts_back_from_yesterday(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    stats = study_service.stats_service()
    _study_new_on(study_service, deck.id, -3, range(1, 3))
    _study_new_on(study_service, deck.id, -2, range(3, 5))
    _study_new_on(study_service, deck.id, -1, range(5, 7))

    # today not studied yet: streak still runs through yesterday
    assert stats.report(deck.id, NOON).streak_days == 3

    _study_new_on(study_service, deck.id, -6, range(7, 9))  # older, with a gap
    assert stats.report(deck.id, NOON).streak_days == 3


def test_retention_ignores_first_reviews(study_service: StudyService) -> None:
    deck = study_service.default_deck()
    stats = study_service.stats_service()
    study_service.add_kanji(deck.id, 1, NOON)

    item = study_service.start_session(deck.id, NOON)[0]
    study_service.answer(item.card, Rating.AGAIN, NOON)  # first review -> not "mature"

    later = NOON + timedelta(days=1)
    nxt = next(i for i in study_service.start_session(deck.id, later) if i.card.id == item.card.id)
    study_service.answer(nxt.card, Rating.GOOD, later)

    report = stats.report(deck.id, later + timedelta(hours=1))
    assert report.mature_reviews == 1
    assert report.retention == 1.0


def test_jlpt_progress(study_service: StudyService, reference_repo: KanjiRepo) -> None:
    deck = study_service.default_deck()
    stats = study_service.stats_service()
    n5_ids = [k.id for k in reference_repo.find(jlpt=5)[:2]]
    study_service.add_kanji(deck.id, n5_ids[0], NOON)  # in deck, still new
    study_service.add_kanji(deck.id, n5_ids[1], NOON)
    item = study_service.start_session(deck.id, NOON)[0]
    study_service.answer(item.card, Rating.GOOD, NOON)  # one N5 kanji now learning

    n5 = next(row for row in stats.report(deck.id, NOON).jlpt if row.level == 5)
    assert n5.total == 103
    assert n5.in_deck == 2
    assert n5.learned == 1


def test_forecast_has_expected_length(study_service: StudyService) -> None:
    report = study_service.stats_service().report(study_service.default_deck().id, NOON)
    assert len(report.forecast) == 14
    assert report.forecast[0].day == NOON.date()
