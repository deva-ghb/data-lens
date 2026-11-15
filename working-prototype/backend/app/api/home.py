"""Home: the role's brief, the decisions waiting for this person, and the site clock."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.client import ai_available
from app.ai.context import answer_question, build_context, focus_shift
from app.ai.drafts import get_or_draft
from app.api.common import LOCAL, SessionDep, UserDep, draft_out, shift_out
from app.clock import site_now
from app.engine.run import latest_run
from app.models import (
    Activity,
    Assignment,
    AssignmentScore,
    Gang,
    Permit,
    PermitEvent,
    Person,
    Role,
    Shift,
    SwapProposal,
    WarningRecord,
    WarningStep,
    Zone,
)
from app.models.permits import PermitStatus
from app.models.scores import SwapStatus, Tier
from app.models.warnings import WarningStatus, WarningStepStatus
from app.views.readiness import permit_readiness

router = APIRouter(tags=["home"])


@router.get("/meta")
def meta(session: SessionDep, user: UserDep) -> dict[str, Any]:
    now = site_now(session)
    nxt = session.scalars(
        select(Shift).where(Shift.start_at > now).order_by(Shift.start_at)
    ).first()
    current = session.scalars(
        select(Shift).where(Shift.start_at <= now, Shift.end_at > now)
    ).first()
    return {
        "site_now": now.isoformat(),
        "site_now_local": (now + LOCAL).isoformat(),
        "current_shift": shift_out(current),
        "next_shift": shift_out(nxt),
        "focus_shift": shift_out(focus_shift(session)),
        "ai_available": ai_available(),
    }


def _decisions(session, user: Person) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    out: list[dict[str, Any]] = []
    role = user.role
    if role == Role.PLANNER:
        rows = session.execute(
            select(SwapProposal, Person, Activity)
            .join(Assignment, Assignment.id == SwapProposal.assignment_id)
            .join(Person, Person.id == Assignment.person_id)
            .join(Activity, Activity.id == SwapProposal.to_activity_id)
            .where(SwapProposal.status == SwapStatus.PROPOSED)
            .order_by(SwapProposal.id)
        ).all()
        for sp, p, a in rows[:3]:
            out.append(
                {
                    "title": f"Swap {p.first_name} {p.last_name} to {a.name.lower()}",
                    "detail": sp.reason,
                    "link": "/roster",
                    "tone": "critical",
                }
            )
    if role == Role.SHIFT_MANAGER:
        rows = session.execute(
            select(SwapProposal, Person)
            .join(Assignment, Assignment.id == SwapProposal.assignment_id)
            .join(Person, Person.id == Assignment.person_id)
            .where(SwapProposal.status == SwapStatus.ACCEPTED)
        ).all()
        for sp, p in rows[:3]:
            out.append(
                {
                    "title": f"Approve the swap for {p.first_name} {p.last_name}",
                    "detail": sp.reason,
                    "link": "/swaps",
                    "tone": "critical",
                }
            )
    if role == Role.HSE_HEAD:
        open_records = session.execute(
            select(WarningRecord, Zone)
            .join(Zone, Zone.id == WarningRecord.zone_id)
            .where(WarningRecord.status == WarningStatus.OPEN)
        ).all()
        for record, zone in open_records:
            drafted = session.scalars(
                select(WarningStep.step).where(
                    WarningStep.warning_id == record.id,
                    WarningStep.status == WarningStepStatus.DRAFTED,
                )
            ).all()
            detected = session.scalar(
                select(WarningStep.id).where(
                    WarningStep.warning_id == record.id,
                    WarningStep.step == 1,
                    WarningStep.status == WarningStepStatus.CONFIRMED,
                )
            )
            out.insert(
                0,
                {
                    "title": f"Early warning in {zone.name}: "
                    + ("continue the record" if detected else "confirm the detection"),
                    "detail": f"{len(drafted)} sections drafted and waiting for you.",
                    "link": f"/warnings/{record.id}",
                    "tone": "critical",
                },
            )
    if role == Role.PERMIT_ISSUER:
        # Step 8 of a warning (permits affected) is the issuer's to sign once controls are set.
        waiting = session.execute(
            select(WarningRecord, Zone)
            .join(Zone, Zone.id == WarningRecord.zone_id)
            .where(WarningRecord.status == WarningStatus.OPEN)
        ).all()
        for record, zone in waiting:
            steps = dict(
                session.execute(
                    select(WarningStep.step, WarningStep.status).where(
                        WarningStep.warning_id == record.id, WarningStep.step.in_([7, 8])
                    )
                ).all()
            )
            if (
                steps.get(7) == WarningStepStatus.CONFIRMED
                and steps.get(8) != WarningStepStatus.CONFIRMED
            ):
                out.append(
                    {
                        "title": f"Early warning in {zone.name}: confirm the permits affected",
                        "detail": "The controls are agreed. Your section sets the permit conditions.",
                        "link": f"/warnings/{record.id}",
                        "tone": "critical",
                    }
                )
        shift = focus_shift(session)
        if shift is not None:
            for permit in session.scalars(
                select(Permit).where(
                    Permit.shift_id == shift.id,
                    Permit.status.in_([PermitStatus.REQUESTED, PermitStatus.ASSESSED]),
                )
            ):
                r = permit_readiness(session, permit)
                if r["crew_status"] == "red":
                    out.append(
                        {
                            "title": f"Hold {permit.number} until the swap is settled",
                            "detail": f"Open swaps on this crew: {r['open_reassignments']}.",
                            "link": f"/permits/{permit.id}",
                            "tone": "critical",
                        }
                    )
                elif len(out) < 3:
                    out.append(
                        {
                            "title": f"Assess {permit.number}",
                            "detail": f"Crew status {r['crew_status']}.",
                            "link": f"/permits/{permit.id}",
                            "tone": "neutral",
                        }
                    )
    if role == Role.CLINICIAN:
        shift = focus_shift(session)
        run = latest_run(session, shift.id) if shift else None
        if run is not None:
            refer = (
                session.execute(
                    select(Person)
                    .join(Assignment, Assignment.person_id == Person.id)
                    .join(AssignmentScore, AssignmentScore.assignment_id == Assignment.id)
                    .where(AssignmentScore.run_id == run.id, AssignmentScore.tier == Tier.REFER)
                )
                .scalars()
                .all()
            )
            for p in refer[:3]:
                out.append(
                    {
                        "title": f"See {p.first_name} {p.last_name} before the shift",
                        "detail": "Referred for occupational health screening.",
                        "link": "/health",
                        "tone": "warning",
                    }
                )
    if role == Role.FOREMAN:
        gangs = session.scalars(select(Gang.id).where(Gang.foreman_id == user.id)).all()
        pending = session.scalars(
            select(PermitEvent).where(PermitEvent.kind == "work_rest_change_pending")
        ).all()
        if gangs and pending:
            out.append(
                {
                    "title": "Confirm the work-rest change",
                    "detail": pending[-1].text,
                    "link": "/m/foreman",
                    "tone": "critical",
                }
            )
    return out[:3]


@router.get("/home")
def home(session: SessionDep, user: UserDep) -> dict[str, Any]:
    day = (site_now(session) + LOCAL).date()
    context = build_context(session, user, "brief")
    brief = get_or_draft(
        session, "brief", f"brief-{day:%Y%m%d}", user.id, context, actor_id=user.id
    )
    session.commit()
    return {
        "role": user.role.value,
        "name": user.first_name,
        "brief": draft_out(session, brief),
        "decisions": _decisions(session, user),
    }


class QuestionBody(BaseModel):
    text: str


@router.post("/home/question")
def question(body: QuestionBody, session: SessionDep, user: UserDep) -> dict[str, Any]:
    text = body.text.strip()
    if not text:
        from app.errors import ApiError

        raise ApiError(422, "invalid_input", "Please type a question.")
    reply = answer_question(session, user, text[:500])
    session.commit()
    return {
        "text": reply.text,
        "declined": reply.declined,
        "note": reply.note,
        "draft": draft_out(session, reply.draft),
    }
