"""The phone review API plus the static page that uses it.

One :class:`StudyService` serves every request. Its SQLite connections are opened
with ``check_same_thread=False`` (FastAPI runs sync endpoints on worker threads), so
every use of it goes through ``lock``. Each request re-reads settings because the
desktop app may have changed the review mode or current deck in the meantime.
"""

from __future__ import annotations

import threading
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles

from kanji_app.core.models import Rating
from kanji_app.services.study import StudyService
from kanji_app.web.schemas import (
    RateIn,
    ReviewState,
    SubmitIn,
    SubmitOut,
    card_out,
    summary_out,
)

STATIC_DIR = Path(__file__).with_name("static")


def create_app(study: StudyService) -> FastAPI:
    app = FastAPI(title="Kanji App reviews")
    lock = threading.Lock()

    @app.middleware("http")
    async def no_store(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/review")
    def review_state() -> ReviewState:
        with lock:
            settings = study.reload_settings()
            deck = study.current_deck()
            item = study.next_item(deck.id)
            summary = study.today_summary(deck.id)
        reveal_mode = settings.review_input == "reveal"
        return ReviewState(
            deck_id=deck.id,
            deck_name=deck.name,
            input_mode=settings.review_input,
            summary=summary_out(summary),
            card=card_out(item, with_answer=reveal_mode) if item else None,
        )

    @app.post("/api/review/{card_id}/rate", status_code=204)
    def rate(card_id: int, body: RateIn) -> None:
        with lock:
            found = study.answer_card(card_id, Rating(body.rating), elapsed_ms=body.elapsed_ms)
        if not found:
            raise HTTPException(status_code=404, detail="card not found")

    @app.post("/api/review/{card_id}/submit")
    def submit(card_id: int, body: SubmitIn) -> SubmitOut:
        with lock:
            study.reload_settings()
            result = study.submit_answer(card_id, body.response, elapsed_ms=body.elapsed_ms)
        if result is None:
            raise HTTPException(status_code=404, detail="card not found")
        return SubmitOut(correct=result.correct, card=card_out(result.item, with_answer=True))

    # Mounted last so the /api routes above take precedence.
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
