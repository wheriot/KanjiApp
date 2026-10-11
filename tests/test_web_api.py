from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kanji_app.core.romaji import to_romaji
from kanji_app.services.settings import AppSettings
from kanji_app.services.study import StudyService, open_study_service
from kanji_app.web.app import create_app


@pytest.fixture
def web_study(tmp_path: Path) -> Iterator[StudyService]:
    # the test client calls the app from another thread, like uvicorn's workers
    service = open_study_service(tmp_path, check_same_thread=False)
    try:
        yield service
    finally:
        service.close()


@pytest.fixture
def client(web_study: StudyService) -> TestClient:
    return TestClient(create_app(web_study))


def _add_kanji(study: StudyService, *ids: int) -> int:
    deck = study.current_deck()
    for kid in ids:
        study.add_kanji(deck.id, kid)
    return deck.id


def test_page_and_icons_are_served(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert "Kanji Reviews" in page.text
    assert client.get("/app.js").status_code == 200
    assert client.get("/icon-180.png").headers["content-type"] == "image/png"


def test_empty_deck_reports_no_card(client: TestClient) -> None:
    state = client.get("/api/review").json()
    assert state["card"] is None
    assert state["input_mode"] == "reveal"
    assert state["summary"]["resets_at"] is not None


def test_api_responses_are_not_cached(client: TestClient) -> None:
    assert client.get("/api/review").headers["cache-control"] == "no-store"


def test_reveal_mode_sends_the_answer_and_rating_advances(
    client: TestClient, web_study: StudyService
) -> None:
    _add_kanji(web_study, 1)
    first = client.get("/api/review").json()
    card = first["card"]
    assert card["answer"]  # flipped on the phone, no round trip
    assert first["summary"]["new_available"] == 2

    response = client.post(f"/api/review/{card['id']}/rate", json={"rating": 3, "elapsed_ms": 4200})
    assert response.status_code == 204

    second = client.get("/api/review").json()
    assert second["card"]["id"] != card["id"]
    history = web_study.review_history(second["deck_id"])
    assert history[0].log.elapsed_ms == 4200


def test_rating_is_validated_and_unknown_cards_404(client: TestClient) -> None:
    assert client.post("/api/review/1/rate", json={"rating": 7}).status_code == 422
    assert client.post("/api/review/999999/rate", json={"rating": 3}).status_code == 404
    assert client.post("/api/review/999999/submit", json={"response": "x"}).status_code == 404


def test_choose_mode_hides_the_answer_and_grades_on_the_server(
    client: TestClient, web_study: StudyService
) -> None:
    web_study.update_settings(AppSettings(review_input="choose"))
    deck_id = _add_kanji(web_study, 1, 2, 3)
    state = client.get("/api/review").json()
    card = state["card"]
    assert state["input_mode"] == "choose"
    assert card["answer"] == "" and card["stroke_svg"] is None
    assert len(card["options"]) > 1

    expected = web_study.next_item(deck_id)
    assert expected is not None
    result = client.post(f"/api/review/{card['id']}/submit", json={"response": expected.answer})
    body = result.json()
    assert body["correct"] is True
    assert body["card"]["answer"] == expected.answer


def test_type_mode_accepts_romaji(client: TestClient, web_study: StudyService) -> None:
    web_study.update_settings(AppSettings(review_input="type"))
    deck_id = _add_kanji(web_study, 1)
    card = client.get("/api/review").json()["card"]
    expected = web_study.next_item(deck_id)
    assert expected is not None and expected.accepted

    wrong = client.post(f"/api/review/{card['id']}/submit", json={"response": "zzz"}).json()
    assert wrong["correct"] is False
    right_card = client.get("/api/review").json()["card"]
    right_item = web_study.next_item(deck_id)
    assert right_item is not None
    right = client.post(
        f"/api/review/{right_card['id']}/submit",
        json={"response": to_romaji(right_item.accepted[0])},
    ).json()
    assert right["correct"] is True


def test_follows_the_desktop_deck_and_mode_without_a_restart(
    client: TestClient, web_study: StudyService, tmp_path: Path
) -> None:
    other = web_study.create_deck("Vocab")
    desktop = open_study_service(tmp_path)  # a second process, like the desktop app
    try:
        desktop.set_current_deck(other.id)
        desktop.update_settings(AppSettings(review_input="type"))
    finally:
        desktop.close()

    state = client.get("/api/review").json()
    assert state["deck_name"] == "Vocab"
    assert state["input_mode"] == "type"
