"""The worker's and the foreman's phones."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.context import focus_shift
from app.ai.drafts import get_or_draft
from app.api.common import SessionDep, UserDep, conflict, not_found, shift_out
from app.audit import audit
from app.clock import site_now
from app.engine.run import latest_run
from app.errors import ApiError
from app.models import (
    Activity,
    Assignment,
    AssignmentScore,
    AuditEntry,
    CheckIn,
    Contest,
    FitnessOutcome,
    Gang,
    LearningItem,
    LearningRead,
    Permit,
    PermitEvent,
    Person,
    Role,
    Shift,
    SwapProposal,
    UnwellEvent,
    Zone,
)
from app.models.learning import LearningStatus
from app.models.roster import Feeling
from app.models.scores import ContestStatus, SwapStatus
from app.policy.tokens import person_token, shift_token

router = APIRouter(prefix="/phone", tags=["phone"])


def _my_assignment(session, user: Person) -> Assignment | None:  # type: ignore[no-untyped-def]
    now = site_now(session)
    shifts = [s for s in (focus_shift(session),) if s is not None]
    running = session.scalars(
        select(Shift).where(Shift.start_at <= now, Shift.end_at > now)
    ).first()
    upcoming = session.scalars(
        select(Shift).where(Shift.start_at > now).order_by(Shift.start_at).limit(3)
    ).all()
    for shift in [*([running] if running else []), *shifts, *upcoming]:
        a = session.scalars(
            select(Assignment).where(
                Assignment.person_id == user.id, Assignment.shift_id == shift.id
            )
        ).first()
        if a is not None:
            return a
    return None


def _score(session, a: Assignment) -> AssignmentScore | None:  # type: ignore[no-untyped-def]
    run = latest_run(session, a.shift_id)
    if run is None:
        return None
    return session.scalars(
        select(AssignmentScore).where(
            AssignmentScore.run_id == run.id, AssignmentScore.assignment_id == a.id
        )
    ).first()


def _my_outcome(session, user: Person) -> dict[str, Any] | None:  # type: ignore[no-untyped-def]
    o = session.scalars(
        select(FitnessOutcome)
        .where(FitnessOutcome.person_id == user.id)
        .order_by(FitnessOutcome.at.desc())
    ).first()
    if o is None or o.at < site_now(session) - timedelta(days=30):
        return None
    return {
        "id": o.id,
        "outcome": o.outcome.value,
        "shared": o.share_with_employer,
        "at": o.at.isoformat(),
    }


class ConsentBody(BaseModel):
    outcome_id: int
    share: bool


@router.post("/consent")
def consent(body: ConsentBody, session: SessionDep, user: UserDep) -> dict[str, Any]:
    """The worker decides whether the employer sees the clinician's outcome (never the reason)."""
    o = session.get(FitnessOutcome, body.outcome_id)
    if o is None or o.person_id != user.id:
        raise not_found("outcome")
    o.share_with_employer = body.share
    audit(session, None, "outcome_consent_changed", "person", person_token(user.id))
    session.commit()
    return {"shared": o.share_with_employer}


@router.get("/me")
def me(session: SessionDep, user: UserDep) -> dict[str, Any]:
    a = _my_assignment(session, user)
    out: dict[str, Any] = {
        "name": user.first_name,
        "language": user.display_language,
        "assignment": None,
        "checked_in": False,
        "tier": None,
        "reason_en": None,
        "reason_local": None,
        "swap_to": None,
        "contest": None,
    }
    cards = session.scalars(
        select(LearningItem.id).where(
            LearningItem.status == LearningStatus.PUBLISHED, LearningItem.kind == "card"
        )
    ).all()
    read = set(
        session.scalars(select(LearningRead.item_id).where(LearningRead.person_id == user.id))
    )
    out["cards_unread"] = len([c for c in cards if c not in read])
    out["outcome"] = _my_outcome(session, user)
    if a is None:
        return out
    shift = session.get_one(Shift, a.shift_id)
    activity = session.get_one(Activity, a.activity_id)
    zone = session.get(Zone, a.zone_id) if a.zone_id else None
    out["assignment"] = {
        "id": a.id,
        "shift": shift_out(shift),
        "activity": activity.name,
        "zone": zone.name if zone else None,
    }
    out["checked_in"] = (
        session.scalars(
            select(CheckIn.id).where(CheckIn.person_id == user.id, CheckIn.shift_id == shift.id)
        ).first()
        is not None
    )
    s = _score(session, a)
    if s is None:
        return out
    out["tier"] = s.tier.value
    swap = session.scalars(
        select(SwapProposal)
        .where(SwapProposal.assignment_id == a.id)
        .order_by(SwapProposal.id.desc())
    ).first()
    moved = swap is not None and swap.to_activity_id != swap.from_activity_id
    if swap is not None and moved and swap.status == SwapStatus.APPROVED:
        out["swap_to"] = session.get_one(Activity, swap.to_activity_id).name
    reason = next((d.get("reason", "") for d in s.drivers_json if d.get("name") == "reason"), "")
    context = {
        "name": user.first_name,
        "tier": s.tier.value,
        "work_reasons": reason,
        "proposed_work": out["swap_to"],
        "today": activity.name,
    }
    if s.tier.value != "fit":
        out["reason_en"] = (
            get_or_draft(
                session,
                "reason_translation",
                f"assignment-{s.tier.value}",
                a.id,
                context,
                "en",
                user.id,
            ).content
            or reason
        )
        if user.display_language != "en":
            out["reason_local"] = (
                get_or_draft(
                    session,
                    "reason_translation",
                    f"assignment-{s.tier.value}",
                    a.id,
                    context,
                    user.display_language,
                    user.id,
                ).content
                or None
            )
    contest = session.scalars(select(Contest).where(Contest.assignment_score_id == s.id)).first()
    out["contest"] = (
        None if contest is None else {"status": contest.status.value, "text": contest.text}
    )
    out["outcome"] = _my_outcome(session, user)
    session.commit()
    return out


class CheckinBody(BaseModel):
    sleep_band: str
    feeling: str
    hydration_ok: bool


@router.post("/checkin", status_code=201)
def checkin(body: CheckinBody, session: SessionDep, user: UserDep) -> dict[str, Any]:
    a = _my_assignment(session, user)
    if a is None:
        raise not_found("shift for you")
    if body.sleep_band not in ("under_5", "5_to_6", "6_to_7", "7_plus"):
        raise ApiError(422, "invalid_input", "Choose how long you slept.")
    try:
        feeling = Feeling(body.feeling)
    except ValueError:
        raise ApiError(422, "invalid_input", "Choose how you feel.") from None
    if session.scalars(
        select(CheckIn.id).where(CheckIn.person_id == user.id, CheckIn.shift_id == a.shift_id)
    ).first():
        raise conflict("You have already checked in for this shift.")
    session.add(
        CheckIn(
            person_id=user.id,
            shift_id=a.shift_id,
            at=site_now(session),
            sleep_hours_band=body.sleep_band,
            feeling=feeling,
            hydration_ok=body.hydration_ok,
        )
    )
    audit(session, user, "checked_in", "shift", str(a.shift_id))
    session.commit()
    return {"checked_in": True}


class ContestBody(BaseModel):
    text: str


@router.post("/contest", status_code=201)
def contest(body: ContestBody, session: SessionDep, user: UserDep) -> dict[str, Any]:
    a = _my_assignment(session, user)
    s = _score(session, a) if a else None
    if s is None:
        raise not_found("change to contest")
    if not body.text.strip():
        raise ApiError(422, "invalid_input", "Say in a few words why you disagree.")
    if s.tier.value == "fit":
        raise conflict("There is no change to contest.")
    if session.scalars(
        select(Contest.id).where(
            Contest.assignment_score_id == s.id, Contest.status == ContestStatus.OPEN
        )
    ).first():
        raise conflict("You have already contested this. The planner will reply.")
    session.add(
        Contest(
            assignment_score_id=s.id,
            person_id=user.id,
            text=body.text.strip()[:600],
            status=ContestStatus.OPEN,
        )
    )
    audit(session, user, "tier_contested", "assignment", str(a.id))
    session.commit()
    return {"status": "open"}


def _crew_permit(session, a: Assignment) -> Permit | None:  # type: ignore[no-untyped-def]
    return session.scalars(
        select(Permit).where(
            Permit.shift_id == a.shift_id,
            Permit.activity_id == a.activity_id,
            Permit.zone_id == a.zone_id,
        )
    ).first()


@router.post("/unwell", status_code=201)
def unwell(session: SessionDep, user: UserDep) -> dict[str, Any]:
    a = _my_assignment(session, user)
    if a is None:
        raise not_found("shift for you")
    now = site_now(session)
    permit = _crew_permit(session, a)
    session.add(
        UnwellEvent(
            person_id=user.id, shift_id=a.shift_id, at=now, permit_id=permit.id if permit else None
        )
    )
    if permit is not None:
        session.add(
            PermitEvent(
                permit_id=permit.id,
                at=now,
                kind="worker_unwell",
                text="A crew member reported feeling unwell and went to the cool room. The clinician has been told.",
                actor_id=None,
            )
        )
    # No name in the trail: the permit and the audit show only that a crew member was unwell.
    audit(session, None, "reported_unwell", "reassignment", shift_token(user.id, a.shift_id))
    session.commit()
    return {
        "told": ["clinician"],
        "next": "Go to the cool room and drink water. The clinic will call you.",
    }


# --- foreman ------------------------------------------------------------------------------


def _foreman(user: Person) -> Person:
    if user.role != Role.FOREMAN:
        raise ApiError(403, "forbidden", "This view is for foremen.")
    return user


def _confirmed_ids(session) -> set[str]:  # type: ignore[no-untyped-def]
    return set(
        session.scalars(
            select(AuditEntry.subject_ref).where(AuditEntry.action == "work_rest_confirmed")
        )
    )


@router.get("/foreman")
def foreman(session: SessionDep, user: UserDep) -> dict[str, Any]:
    _foreman(user)
    gangs = session.scalars(select(Gang).where(Gang.foreman_id == user.id)).all()
    shift = focus_shift(session)
    crew, zones, controls = [], set(), 0
    run = latest_run(session, shift.id) if shift else None
    for gang in gangs:
        for a, p, act in session.execute(
            select(Assignment, Person, Activity)
            .join(Person, Person.id == Assignment.person_id)
            .join(Activity, Activity.id == Assignment.activity_id)
            .where(
                Assignment.gang_id == gang.id, Assignment.shift_id == (shift.id if shift else -1)
            )
        ):
            crew.append(
                {"name": f"{p.first_name} {p.last_name}", "task": act.name, "gang": gang.name}
            )
            zones.add(a.zone_id)
            if run is not None:
                sc = session.scalars(
                    select(AssignmentScore).where(
                        AssignmentScore.run_id == run.id, AssignmentScore.assignment_id == a.id
                    )
                ).first()
                if sc is not None and sc.tier.value == "fit_with_controls":
                    controls += 1
    actions = []
    if controls:
        actions.append(
            f"Pair {controls} crew members with a buddy on the high platforms and hold the extra water break at 01:00."
        )
    confirmed = _confirmed_ids(session)
    pending = []
    for e in session.scalars(
        select(PermitEvent)
        .join(Permit, Permit.id == PermitEvent.permit_id)
        .where(PermitEvent.kind == "work_rest_change_pending", Permit.zone_id.in_(zones or {-1}))
    ):
        if str(e.id) not in confirmed:
            permit = session.get_one(Permit, e.permit_id)
            pending.append(
                {"id": e.id, "permit": permit.number, "text": e.text, "at": e.at.isoformat()}
            )
    return {
        "gangs": [g.name for g in gangs],
        "shift": shift_out(shift),
        "crew": crew,
        "actions": actions,
        "pending": pending,
    }


@router.post("/foreman/confirm/{event_id}")
def confirm(event_id: int, session: SessionDep, user: UserDep) -> dict[str, Any]:
    _foreman(user)
    e = session.get(PermitEvent, event_id)
    if e is None or e.kind != "work_rest_change_pending":
        raise not_found("change")
    if str(e.id) in _confirmed_ids(session):
        raise conflict("Already confirmed.")
    session.add(
        PermitEvent(
            permit_id=e.permit_id,
            at=site_now(session),
            kind="work_rest_change_confirmed",
            text="Work-rest change confirmed by the foreman on deck.",
            actor_id=user.id,
        )
    )
    audit(session, user, "work_rest_confirmed", "permit_event", str(e.id))
    session.commit()
    return {"confirmed": True}


__all__ = ["router", "timedelta"]
