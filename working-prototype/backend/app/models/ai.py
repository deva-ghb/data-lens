"""Stored AI drafts and images, with their provenance."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AiDraftStatus(enum.StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    UNAVAILABLE = "unavailable"


class AiDraft(Base):
    __tablename__ = "ai_drafts"
    __table_args__ = (
        # The lookup used to reuse a stored draft instead of calling the model again.
        Index(None, "kind", "subject_kind", "subject_id", "prompt_version", "language"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    subject_kind: Mapped[str] = mapped_column(String(32))
    subject_id: Mapped[int]
    # Language of the content, for drafts such as a reason in the worker's language.
    language: Mapped[str] = mapped_column(String(16), default="en")
    prompt_version: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    deployment: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    sure_json: Mapped[list[Any]]
    unsure_json: Mapped[list[Any]]
    would_change_json: Mapped[list[Any]]
    confidence: Mapped[float]
    reasoning_json: Mapped[dict[str, Any]]
    status: Mapped[AiDraftStatus] = mapped_column(default=AiDraftStatus.DRAFT)
    created_at: Mapped[datetime]


class AiImage(Base):
    __tablename__ = "ai_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    subject_id: Mapped[int] = mapped_column(index=True)
    path: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(64))
    prompt: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime]


class AiDecision(Base):
    """Typed answers from the Decisions API (probabilities, choices, scores) with provenance."""

    __tablename__ = "ai_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_kind: Mapped[str] = mapped_column(String(32))
    subject_id: Mapped[int] = mapped_column(index=True)
    model: Mapped[str] = mapped_column(String(64))
    questions_json: Mapped[list[Any]]
    answers_json: Mapped[list[Any]]
    created_at: Mapped[datetime]
