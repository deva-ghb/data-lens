"""The audit trail for the seeded history.

The history is written straight into the tables, so nothing passed through the code that
audits a live action. This walks what was written and adds the entries those actions
would have left, each stamped at the time it happened, so the audit screen tells the
same story as the records.
"""

from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Action,
    AiDraft,
    AuditEntry,
    LearningItem,
    Person,
    WarningRecord,
    WarningStep,
)
from app.models.actions import ActionStatus
from app.models.ai import AiDraftStatus
from app.models.learning import LearningStatus
from app.models.warnings import WarningStatus, WarningStepStatus

HSE_HEAD = "layla.haddad"
# Site time is UTC+4; a morning sign-off at 10:00 local is 06:00 UTC.
MORNING_UTC = time(6, 0)


def _entry(
    session: Session,
    at: datetime,
    actor: Person | None,
    action: str,
    subject_kind: str,
    subject_ref: str,
    evidence: dict[str, Any] | None = None,
    model_version: str | None = None,
) -> None:
    session.add(
        AuditEntry(
            at=at,
            actor_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            action=action,
            subject_kind=subject_kind,
            subject_ref=subject_ref,
            evidence_json=evidence,
            model_version=model_version,
        )
    )


def write_audit_history(session: Session) -> None:
    hse_head = session.scalars(select(Person).where(Person.email.startswith(f"{HSE_HEAD}@"))).one()

    for d in session.scalars(select(AiDraft)):
        _entry(
            session,
            d.created_at,
            None,
            "ai_draft",
            d.subject_kind,
            str(d.subject_id),
            {"kind": d.kind, "draft_id": d.id, "language": d.language},
            f"{d.model} prompt {d.kind} v{d.prompt_version}",
        )

    step_confirmer: dict[tuple[int, int], Person] = {}
    for s in session.scalars(
        select(WarningStep).where(WarningStep.status == WarningStepStatus.CONFIRMED)
    ):
        actor = session.get(Person, s.confirmed_by) if s.confirmed_by else hse_head
        assert actor is not None
        step_confirmer[(s.warning_id, s.step)] = actor
        at = s.confirmed_at or datetime.min
        _entry(
            session,
            at,
            actor,
            "warning_step_confirmed",
            "warning",
            str(s.warning_id),
            {"step": s.step},
        )

    for w in session.scalars(
        select(WarningRecord).where(WarningRecord.status == WarningStatus.CLOSED)
    ):
        actor = step_confirmer.get((w.id, 10), hse_head)
        outcome = w.outcome.value if w.outcome else None
        _entry(
            session,
            w.closed_at or w.opened_at,
            actor,
            "warning_closed",
            "warning",
            str(w.id),
            {"outcome": outcome},
        )

    for a in session.scalars(select(Action)):
        created_by = (
            step_confirmer.get((a.source_id, 7), hse_head)
            if a.source_kind == "warning"
            else hse_head
        )
        created_at = _action_created_at(session, a)
        _entry(
            session,
            created_at,
            created_by,
            "action_created",
            a.source_kind,
            str(a.source_id),
            {"action": a.id},
        )
        owner = session.get(Person, a.owner_id)
        if a.status == ActionStatus.DONE:
            _entry(
                session,
                datetime.combine(a.due_on, MORNING_UTC),
                owner,
                "action_updated",
                a.source_kind,
                str(a.source_id),
                {"action": a.id, "status": "done", "effective": None},
            )
        if a.effective is not None and a.effectiveness_check_on:
            _entry(
                session,
                datetime.combine(a.effectiveness_check_on, MORNING_UTC),
                owner,
                "action_updated",
                a.source_kind,
                str(a.source_id),
                {"action": a.id, "status": a.status.value, "effective": a.effective},
            )

    for d in session.scalars(
        select(AiDraft).where(
            AiDraft.kind == "incident_record", AiDraft.status == AiDraftStatus.CONFIRMED
        )
    ):
        _entry(
            session,
            d.created_at + timedelta(hours=3),
            hse_head,
            "report_confirmed",
            d.subject_kind,
            str(d.subject_id),
        )

    for item in session.scalars(
        select(LearningItem).where(LearningItem.status == LearningStatus.PUBLISHED)
    ):
        draft = session.get(AiDraft, item.draft_id) if item.draft_id else None
        if draft is None:
            continue
        _entry(
            session,
            draft.created_at + timedelta(days=1),
            hse_head,
            "learning_shared",
            "learning",
            str(item.id),
        )
    session.flush()


def _action_created_at(session: Session, a: Action) -> datetime:
    """When step 7 of the source warning was confirmed; otherwise a week before it was due."""
    if a.source_kind == "warning":
        step = session.scalars(
            select(WarningStep).where(WarningStep.warning_id == a.source_id, WarningStep.step == 7)
        ).first()
        if step and step.confirmed_at:
            return step.confirmed_at
    return datetime.combine(a.due_on - timedelta(days=7), MORNING_UTC)
