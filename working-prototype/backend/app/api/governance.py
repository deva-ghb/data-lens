"""Governance and the audit trail (redacted for the Authority)."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.common import SessionDep, UserDep
from app.errors import ApiError
from app.models import AuditEntry, Person, Role
from app.policy.access import can

router = APIRouter(tags=["governance"])


def _audit_reader(user: UserDep) -> Person:
    if not (
        can(user.role, "audit_redacted") or can(user.role, "all_records") or user.role == Role.ADMIN
    ):
        raise ApiError(403, "forbidden", "The audit trail is not available for your role.")
    return user


@router.get("/audit")
def audit_trail(
    session: SessionDep,
    action: str | None = None,
    limit: int = 200,
    user: Person = Depends(_audit_reader),
) -> dict[str, Any]:
    query = select(AuditEntry).order_by(AuditEntry.id.desc()).limit(min(limit, 1000))
    if action:
        query = query.where(AuditEntry.action == action)
    redacted = user.role == Role.AUTHORITY
    entries = []
    for e in session.scalars(query):
        actor = None
        if e.actor_id and not redacted:
            p = session.get(Person, e.actor_id)
            actor = f"{p.first_name} {p.last_name}" if p else None
        entries.append(
            {
                "id": e.id,
                "at": e.at.isoformat(),
                "actor": actor,
                "actor_role": e.actor_role.value if e.actor_role else "system",
                "action": e.action,
                "subject_kind": e.subject_kind,
                "subject_ref": e.subject_ref,
                "model_version": e.model_version,
                "evidence": None if redacted else e.evidence_json,
            }
        )
    return {"redacted": redacted, "entries": entries}
