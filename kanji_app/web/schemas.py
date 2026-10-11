"""JSON shapes for the phone review API, and conversions from service results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from kanji_app.core.kanjivg import render
from kanji_app.services.study import ReviewItem, TodaySummary


class SentenceOut(BaseModel):
    japanese: str
    english: str


class CardOut(BaseModel):
    """A card's faces. Answer-side fields are blank until the card is revealed."""

    id: int
    subject: str
    mode: str
    prompt: str
    prompt_note: str
    answer: str
    answer_note: str
    sentence: SentenceOut | None
    components: str
    mnemonic: str
    stroke_svg: str | None
    options: list[str]


class SummaryOut(BaseModel):
    due: int
    new_available: int
    reviewed_today: int
    capped_new: int
    capped_due: int
    limit_reached: bool
    next_due: datetime | None
    resets_at: datetime | None


class ReviewState(BaseModel):
    deck_id: int
    deck_name: str
    input_mode: str
    summary: SummaryOut
    card: CardOut | None


class RateIn(BaseModel):
    rating: int = Field(ge=1, le=4)
    elapsed_ms: int = Field(default=0, ge=0)


class SubmitIn(BaseModel):
    response: str = Field(max_length=200)
    elapsed_ms: int = Field(default=0, ge=0)


class SubmitOut(BaseModel):
    correct: bool
    card: CardOut


def card_out(item: ReviewItem, *, with_answer: bool) -> CardOut:
    """``with_answer=False`` withholds everything shown only on reveal (choose/type modes
    are graded on the server, so the page never needs the answer up front)."""
    sentence = item.sentence if with_answer else None
    stroke = item.stroke if with_answer else None
    return CardOut(
        id=item.card.id,
        subject=item.card.subject_type.value,
        mode=item.card.mode.value,
        prompt=item.prompt,
        prompt_note=item.prompt_note,
        answer=item.answer if with_answer else "",
        answer_note=item.answer_note if with_answer else "",
        sentence=SentenceOut(japanese=sentence.japanese, english=sentence.english)
        if sentence
        else None,
        components=item.components if with_answer else "",
        mnemonic=item.mnemonic if with_answer else "",
        stroke_svg=render(stroke, ink="currentColor") if stroke else None,
        options=list(item.options),
    )


def summary_out(summary: TodaySummary) -> SummaryOut:
    return SummaryOut(
        due=summary.due,
        new_available=summary.new_available,
        reviewed_today=summary.reviewed_today,
        capped_new=summary.capped_new,
        capped_due=summary.capped_due,
        limit_reached=summary.limit_reached,
        next_due=summary.next_due,
        resets_at=summary.resets_at,
    )
