"""Shared pieces for API routers: session and user dependencies, scope guards, draft output."""

from collections.abc import Callable
from datetime import timedelta
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app import db
from app.auth.deps import current_user
from app.errors import ApiError
from app.models import AiDraft, Person, Shift
from app.policy.access import DataScope, can

SessionDep = Annotated[Session, Depends(db.get_session)]
UserDep = Annotated[Person, Depends(current_user)]
LOCAL = timedelta(hours=4)


def require_scope(*scopes: DataScope) -> Callable[[Person], Person]:
    """Let the request through if the person's role holds any of the scopes; else 403."""

    def guard(user: UserDep) -> Person:
        if not any(can(user.role, s) for s in scopes):
            raise ApiError(403, "forbidden", "This is not available for your role.")
        return user

    return guard


def not_found(what: str) -> ApiError:
    return ApiError(404, "not_found", f"That {what} does not exist.")


def conflict(message: str) -> ApiError:
    return ApiError(409, "conflict", message)


def person_name(session: Session, person_id: int | None) -> str | None:
    if person_id is None:
        return None
    person = session.get(Person, person_id)
    return f"{person.first_name} {person.last_name}" if person else None


def draft_out(
    session: Session, draft: AiDraft | None, confirmed_by: int | None = None
) -> dict[str, Any] | None:
    if draft is None:
        return None
    return {
        "id": str(draft.id) if draft.id is not None else "",
        "kind": draft.kind,
        "content": draft.content,
        "sure": list(draft.sure_json or []),
        "unsure": list(draft.unsure_json or []),
        "would_change": list(draft.would_change_json or []),
        "confidence": draft.confidence,
        "reasoning": draft.reasoning_json
        or {"evidence": [], "rules": [], "inferences": [], "rejected": []},
        "status": getattr(draft.status, "value", draft.status),
        "confirmed_by": person_name(session, confirmed_by),
        "model": draft.model,
    }


def shift_label(shift: Shift) -> str:
    start = shift.start_at + LOCAL
    kind = "Night" if shift.kind.value == "night" else "Day"
    return f"{kind} shift, {start:%a %d %b}, {start:%H:%M}"


def shift_out(shift: Shift | None) -> dict[str, Any] | None:
    if shift is None:
        return None
    return {
        "id": shift.id,
        "date": shift.date.isoformat(),
        "kind": shift.kind.value,
        "start_at": shift.start_at.isoformat(),
        "label": shift_label(shift),
    }
