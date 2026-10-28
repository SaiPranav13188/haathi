"""API request models. Note: no field ever accepts Aadhaar, bank account or phone numbers."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Lang = Literal["en", "hi", "te"]
_ID_LIKE = __import__("re").compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b|\b\d{10}\b|\b\d{9,18}\b")


class FactIn(BaseModel):
    value: Any
    source_text: str = ""
    method: str = "answer"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    lang: Lang = "en"
    profile: dict[str, FactIn] = Field(default_factory=dict)
    pending: list[str] = Field(default_factory=list)
    asked: list[str] = Field(default_factory=list)
    focus: list[str] = Field(default_factory=list)
    skip_questions: bool = False

    @field_validator("message")
    @classmethod
    def _mask_ids(cls, v: str) -> str:
        # Privacy: mask anything that looks like Aadhaar / phone / account numbers before processing.
        return _ID_LIKE.sub("[number removed]", v)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class EvaluateRequest(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    lang: Lang = "en"
    scheme_ids: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class NextRequest(EvaluateRequest):
    asked: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    max_questions: int = 12


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    message: str = Field(default="", max_length=2000)
    answer: str = Field(default="", max_length=8000)
    comment: str = Field(default="", max_length=2000)
    lang: Lang = "en"
