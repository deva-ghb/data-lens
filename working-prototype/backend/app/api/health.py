"""The clinician's screening list and health records, fitness outcomes, and the outcome-only
view other roles get. The employer never sees medical data, only the shared outcome."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.context import focus_shift
from app.api.common import SessionDep, not_found, person_name, require_scope
from app.audit import audit
from app.clock import site_now
from app.engine.run import latest_run
from app.errors import ApiError
from app.models import (
    Assignment,
    AssignmentScore,
    CheckIn,
    FitnessOutcome,
    LabPanel,
    Person,
    Role,
    UnwellEvent,
)
from app.models.health import FitnessDecision
from app.models.scores import Tier

router = APIRouter(tags=["health"])


def _clinician(user: Person = Depends(require_scope("health_detail"))) -> Person:
    if user.role != Role.CLINICIAN:
        raise ApiError(403, "forbidden", "Health detail is for the clinician only.")
    return user


@router.get("/health/screening")
def screening(session: SessionDep, user: Person = Depends(_clinician)) -> list[dict[str, Any]]:
    now = site_now(session)
    items: dict[int, dict[str, Any]] = {}

    def add(pid: int, why: str) -> None:
        if pid not in items:
            p = session.get_one(Person, pid)
            latest = session.scalars(
                select(FitnessOutcome)
                .where(FitnessOutcome.person_id == pid)
                .order_by(FitnessOutcome.at.desc())
            ).first()
            items[pid] = {
                "person_id": pid,
                "worker": f"{p.first_name} {p.last_name}",
                "job": p.job_title,
                "why": why,
                "latest_outcome": latest.outcome.value if latest else None,
            }

    for event in session.scalars(
        select(UnwellEvent).where(
            UnwellEvent.at >= now - timedelta(hours=48), UnwellEvent.at <= now
        )
    ):
        add(event.person_id, "Reported feeling unwell")
    shift = focus_shift(session)
    run = latest_run(session, shift.id) if shift else None
    if run is not None:
        for (pid,) in session.execute(
            select(Assignment.person_id)
            .join(AssignmentScore, AssignmentScore.assignment_id == Assignment.id)
            .where(AssignmentScore.run_id == run.id, AssignmentScore.tier == Tier.REFER)
        ):
            add(pid, "Referred by the engine before the shift")
    for pid in set(
        session.scalars(
            select(LabPanel.person_id).where(
                LabPanel.flag.is_not(None), LabPanel.at >= now - timedelta(days=60)
            )
        )
    ):
        add(pid, "Lab result flagged for review")
    return list(items.values())


@router.get("/health/workers/{person_id}")
def worker_record(
    person_id: int, session: SessionDep, user: Person = Depends(_clinician)
) -> dict[str, Any]:
    p = session.get(Person, person_id)
    if p is None:
        raise not_found("worker")
    panels: dict[str, list[dict[str, Any]]] = {}
    for lab in session.scalars(
        select(LabPanel).where(LabPanel.person_id == person_id).order_by(LabPanel.at)
    ):
        panels.setdefault(lab.panel, []).append(
            {"at": lab.at.isoformat(), "value": lab.value, "flag": lab.flag}
        )
    checkins = session.scalars(
        select(CheckIn).where(CheckIn.person_id == person_id).order_by(CheckIn.at.desc()).limit(14)
    ).all()
    outcomes = session.scalars(
        select(FitnessOutcome)
        .where(FitnessOutcome.person_id == person_id)
        .order_by(FitnessOutcome.at.desc())
    ).all()
    audit(session, user, "health_record_viewed", "person", str(person_id))
    session.commit()
    return {
        "person_id": p.id,
        "worker": f"{p.first_name} {p.last_name}",
        "job": p.job_title,
        "site_arrival_date": p.site_arrival_date.isoformat(),
        "lab_trends": [{"panel": k, "points": v} for k, v in panels.items()],
        "checkins": [
            {
                "at": c.at.isoformat(),
                "sleep": c.sleep_hours_band,
                "feeling": c.feeling.value,
                "hydration_ok": c.hydration_ok,
            }
            for c in checkins
        ],
        "outcomes": [
            {
                "at": o.at.isoformat(),
                "outcome": o.outcome.value,
                "restriction": o.restriction_text,
                "shared": o.share_with_employer,
                "by": person_name(session, o.decided_by),
            }
            for o in outcomes
        ],
    }


class OutcomeBody(BaseModel):
    outcome: str
    restriction_text: str | None = None
    share_with_employer: bool = True


@router.post("/health/workers/{person_id}/outcome", status_code=201)
def record_outcome(
    person_id: int, body: OutcomeBody, session: SessionDep, user: Person = Depends(_clinician)
) -> dict[str, Any]:
    if session.get(Person, person_id) is None:
        raise not_found("worker")
    try:
        decision = FitnessDecision(body.outcome)
    except ValueError:
        raise ApiError(
            422, "invalid_input", "The outcome is fit, fit with restrictions or not today."
        ) from None
    if (
        decision == FitnessDecision.FIT_WITH_RESTRICTIONS
        and not (body.restriction_text or "").strip()
    ):
        raise ApiError(422, "invalid_input", "Say what the restriction is.")
    outcome = FitnessOutcome(
        person_id=person_id,
        decided_by=user.id,
        at=site_now(session),
        outcome=decision,
        restriction_text=(body.restriction_text or "").strip() or None,
        share_with_employer=body.share_with_employer,
    )
    session.add(outcome)
    session.flush()
    audit(
        session,
        user,
        "fitness_outcome",
        "person",
        str(person_id),
        evidence={"outcome": decision.value, "shared": body.share_with_employer},
    )
    session.commit()
    return {"id": outcome.id, "outcome": decision.value, "shared": body.share_with_employer}


@router.get("/fitness-outcomes")
def fitness_outcomes(
    session: SessionDep, user: Person = Depends(require_scope("fitness_outcomes"))
) -> list[dict[str, Any]]:
    now = site_now(session)
    rows = session.execute(
        select(FitnessOutcome, Person)
        .join(Person, Person.id == FitnessOutcome.person_id)
        .where(FitnessOutcome.at >= now - timedelta(days=30))
        .order_by(FitnessOutcome.at.desc())
    ).all()
    return [
        {
            "worker": f"{p.first_name} {p.last_name}",
            "at": o.at.isoformat(),
            "outcome": o.outcome.value if o.share_with_employer else "not shared",
        }
        for o, p in rows
    ]
