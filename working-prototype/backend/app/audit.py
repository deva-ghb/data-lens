"""Write one entry to the append-only audit log."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEntry, Person, SiteClock


def audit(
    session: Session,
    actor: Person | None,
    action: str,
    subject_kind: str,
    subject_ref: str,
    evidence: dict[str, Any] | None = None,
    model_version: str | None = None,
) -> AuditEntry:
    """Record what happened, who did it (None means the system) and the evidence shown.

    For reassignments, pass a shift token as subject_ref so the worker is not named.
    The entry is stamped with the site clock, so audit times line up with the scenario.
    """
    clock = session.get(SiteClock, 1)
    at = clock.now if clock else datetime.now(UTC).replace(tzinfo=None)
    entry = AuditEntry(
        at=at,
        actor_id=actor.id if actor else None,
        actor_role=actor.role if actor else None,
        action=action,
        subject_kind=subject_kind,
        subject_ref=subject_ref,
        evidence_json=evidence,
        model_version=model_version,
    )
    session.add(entry)
    session.flush()
    return entry
