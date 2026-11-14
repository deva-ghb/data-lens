"""Written drafts: generated once per subject, stored with provenance, confirmed by a person.

`get_or_draft` returns a stored draft for the same kind, subject, language and prompt
version. Otherwise it asks the model, checks the answer has the full shape (content,
sure, unsure, what would change it, confidence, reasoning) and stores it. If anything
goes wrong it stores nothing and returns an unsaved draft marked "unavailable", so the
screen can say so and let a person write the section by hand.
"""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import AiUnavailable, respond_json
from app.ai.prompts import load_prompt
from app.ai.schemas import DRAFT_SCHEMA, valid_draft
from app.audit import audit
from app.config import settings
from app.models import AiDraft, Person, SiteClock
from app.models.ai import AiDraftStatus

LANGUAGE_NAMES = {
    "en": "English",
    "ar": "Arabic",
    "hi": "Hindi",
    "ur": "Urdu",
    "ne": "Nepali",
    "bn": "Bengali",
    "ml": "Malayalam",
    "tl": "Tagalog",
    "ta": "Tamil",
}


def _now(session: Session) -> datetime:
    clock = session.get(SiteClock, 1)
    return clock.now if clock else datetime.now(UTC).replace(tzinfo=None)


def unavailable_draft(
    kind: str, subject_kind: str, subject_id: int, language: str = "en"
) -> AiDraft:
    return AiDraft(
        id=None,
        kind=kind,
        subject_kind=subject_kind,
        subject_id=subject_id,
        language=language,
        prompt_version="",
        model="",
        deployment="",
        content="",
        sure_json=[],
        unsure_json=[],
        would_change_json=[],
        confidence=0.0,
        reasoning_json={"evidence": [], "rules": [], "inferences": [], "rejected": []},
        status=AiDraftStatus.UNAVAILABLE,
    )


def stored_draft(
    session: Session, kind: str, subject_kind: str, subject_id: int, language: str = "en"
) -> AiDraft | None:
    version, _ = load_prompt(kind)
    return session.scalars(
        select(AiDraft)
        .where(
            AiDraft.kind == kind,
            AiDraft.subject_kind == subject_kind,
            AiDraft.subject_id == subject_id,
            AiDraft.language == language,
            AiDraft.prompt_version == version,
            AiDraft.status != AiDraftStatus.UNAVAILABLE,
        )
        .order_by(AiDraft.id.desc())
    ).first()


def get_or_draft(
    session: Session,
    kind: str,
    subject_kind: str,
    subject_id: int,
    context: dict[str, Any],
    language: str = "en",
    actor_id: int | None = None,
) -> AiDraft:
    existing = stored_draft(session, kind, subject_kind, subject_id, language)
    if existing is not None:
        return existing
    version, instructions = load_prompt(kind)
    if language != "en":
        instructions += (
            f"\nWrite every text field in {LANGUAGE_NAMES.get(language, language)}, "
            "in simple words a worker reads on a phone."
        )
    prompt = json.dumps(context, default=str, ensure_ascii=False)
    try:
        data = respond_json(instructions, prompt, DRAFT_SCHEMA, name=kind.replace("-", "_"))
    except AiUnavailable:
        return unavailable_draft(kind, subject_kind, subject_id, language)
    if not valid_draft(data):
        return unavailable_draft(kind, subject_kind, subject_id, language)
    draft = AiDraft(
        kind=kind,
        subject_kind=subject_kind,
        subject_id=subject_id,
        language=language,
        prompt_version=version,
        model=settings.ai_text_model,
        deployment=settings.ai_text_model,
        content=data["content"].replace("—", "-"),
        sure_json=data["sure"],
        unsure_json=data["unsure"],
        would_change_json=data["would_change"],
        confidence=float(data["confidence"]),
        reasoning_json=data["reasoning"],
        status=AiDraftStatus.DRAFT,
        created_at=_now(session),
    )
    session.add(draft)
    session.flush()
    actor = session.get(Person, actor_id) if actor_id else None
    audit(
        session,
        actor,
        "ai_draft",
        subject_kind,
        str(subject_id),
        evidence={"kind": kind, "draft_id": draft.id, "language": language},
        model_version=f"{settings.ai_text_model} prompt {kind} v{version}",
    )
    return draft
