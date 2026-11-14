"""Permits to work: the board, a permit with its people-and-conditions block, the lifecycle,
conditions and the people-factor record a permit system would receive."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.context import focus_shift
from app.api.common import SessionDep, conflict, not_found, person_name, require_scope, shift_out
from app.engine.layers import peak_wbgt
from app.errors import ApiError
from app.feeds.wbgt import heat_tier
from app.models import (
    Activity,
    AuditEntry,
    Permit,
    PermitCondition,
    PermitEvent,
    Person,
    Role,
    Shift,
    VesselCall,
    Zone,
)
from app.models.permits import ConditionOrigin, ConditionStatus
from app.models.scores import ConditionsSource
from app.permits.lifecycle import InvalidMove, transition
from app.views.readiness import permit_readiness

router = APIRouter(tags=["permits"])


def _issuer(user: Person = Depends(require_scope("permit_counts"))) -> Person:
    if user.role != Role.PERMIT_ISSUER:
        raise ApiError(403, "forbidden", "Only the permit issuer can change a permit.")
    return user


def _permit(session, permit_id: int) -> Permit:  # type: ignore[no-untyped-def]
    permit = session.get(Permit, permit_id)
    if permit is None:
        raise not_found("permit")
    return permit


def _summary(session, permit: Permit) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    activity = session.get_one(Activity, permit.activity_id)
    zone = session.get_one(Zone, permit.zone_id)
    readiness = permit_readiness(session, permit)
    return {
        "id": permit.id,
        "number": permit.number,
        "activity": activity.name,
        "grade": activity.grade,
        "zone": zone.name,
        "status": permit.status.value,
        "crew_size": readiness["crew_size"],
        "crew_status": readiness["crew_status"],
        "readiness": readiness["readiness"],
    }


@router.get("/permits")
def board(
    session: SessionDep,
    shift_id: int | None = None,
    user: Person = Depends(require_scope("permit_counts")),
) -> dict[str, Any]:
    shift = session.get(Shift, shift_id) if shift_id else focus_shift(session)
    if shift is None:
        raise not_found("shift")
    permits = session.scalars(
        select(Permit).where(Permit.shift_id == shift.id).order_by(Permit.number)
    ).all()
    return {"shift": shift_out(shift), "permits": [_summary(session, p) for p in permits]}


@router.get("/permits/{permit_id}")
def detail(
    permit_id: int, session: SessionDep, user: Person = Depends(require_scope("permit_counts"))
) -> dict[str, Any]:
    permit = _permit(session, permit_id)
    shift = session.get_one(Shift, permit.shift_id)
    peak, _ = peak_wbgt(
        session, shift.start_at - timedelta(hours=12), shift.end_at, ConditionsSource.SCENARIO
    )
    vessel = session.scalars(
        select(VesselCall.vessel_name).where(
            VesselCall.berth_zone_id == permit.zone_id,
            VesselCall.arrives_at < shift.end_at,
            VesselCall.departs_at > shift.start_at,
        )
    ).first()
    conditions = session.scalars(
        select(PermitCondition)
        .where(PermitCondition.permit_id == permit.id)
        .order_by(PermitCondition.id)
    ).all()
    events = session.scalars(
        select(PermitEvent)
        .where(PermitEvent.permit_id == permit.id)
        .order_by(PermitEvent.at, PermitEvent.id)
    ).all()
    return {
        **_summary(session, permit),
        "shift": shift_out(shift),
        "issuer": person_name(session, permit.issuer_id),
        "vessel": vessel,
        "forecast": {"peak_wbgt": peak, "heat_tier": heat_tier(peak) if peak is not None else None},
        "people_factor": permit_readiness(session, permit),
        "conditions": [
            {
                "id": c.id,
                "text": c.text,
                "origin": c.origin.value,
                "status": c.status.value,
                "warning_id": c.warning_id,
            }
            for c in conditions
        ],
        "events": [
            {
                "id": e.id,
                "at": e.at.isoformat(),
                "kind": e.kind,
                "text": e.text,
                "by": person_name(session, e.actor_id),
            }
            for e in events
        ],
    }


class ConditionBody(BaseModel):
    text: str


@router.post("/permits/{permit_id}/conditions", status_code=201)
def add_condition(
    permit_id: int, body: ConditionBody, session: SessionDep, user: Person = Depends(_issuer)
) -> dict[str, Any]:
    permit = _permit(session, permit_id)
    if not body.text.strip():
        raise ApiError(422, "invalid_input", "A condition needs some text.")
    condition = PermitCondition(
        permit_id=permit.id,
        text=body.text.strip(),
        origin=ConditionOrigin.ISSUER,
        status=ConditionStatus.ACCEPTED,
    )
    session.add(condition)
    session.flush()
    from app.audit import audit

    audit(
        session,
        user,
        "permit_condition_added",
        "permit",
        permit.number,
        evidence={"text": condition.text},
    )
    session.commit()
    return {"id": condition.id, "text": condition.text, "status": condition.status.value}


class ConditionPatch(BaseModel):
    text: str | None = None
    status: str | None = None


@router.patch("/permits/{permit_id}/conditions/{condition_id}")
def edit_condition(
    permit_id: int,
    condition_id: int,
    body: ConditionPatch,
    session: SessionDep,
    user: Person = Depends(_issuer),
) -> dict[str, Any]:
    condition = session.get(PermitCondition, condition_id)
    if condition is None or condition.permit_id != permit_id:
        raise not_found("condition")
    if body.text is not None and body.text.strip() and body.text.strip() != condition.text:
        condition.text = body.text.strip()
        condition.status = ConditionStatus.EDITED
    elif body.status in ("accepted", "rejected"):
        condition.status = ConditionStatus(body.status)
    from app.audit import audit

    audit(
        session,
        user,
        "permit_condition_changed",
        "permit",
        str(permit_id),
        evidence={"condition": condition.id, "status": condition.status.value},
    )
    session.commit()
    return {"id": condition.id, "text": condition.text, "status": condition.status.value}


@router.get("/permits/{permit_id}/people-factor.json")
def people_factor(
    permit_id: int, session: SessionDep, user: Person = Depends(require_scope("permit_counts"))
) -> dict[str, Any]:
    permit = _permit(session, permit_id)
    r = permit_readiness(session, permit)
    conditions = session.scalars(
        select(PermitCondition).where(
            PermitCondition.permit_id == permit.id,
            PermitCondition.status != ConditionStatus.REJECTED,
        )
    ).all()
    suspend = next((c.text for c in conditions if c.text.lower().startswith("suspend")), None)
    last_audit = session.scalars(
        select(AuditEntry.id)
        .where(AuditEntry.subject_ref == permit.number)
        .order_by(AuditEntry.id.desc())
    ).first()
    return {
        "permit": permit.number,
        "readiness_counts": r["readiness"],
        "crew_status": r["crew_status"],
        "drivers": r["top_drivers"],
        "added_controls": [c.text for c in conditions],
        "confidence": r["confidence"],
        "closing_condition": suspend,
        "audit_reference": f"audit-{last_audit}" if last_audit else None,
    }


# Registered last so the specific routes above (conditions, people-factor) win.
class MoveBody(BaseModel):
    reason: str | None = None


@router.post("/permits/{permit_id}/{move}")
def move(
    permit_id: int, move: str, body: MoveBody, session: SessionDep, user: Person = Depends(_issuer)
) -> dict[str, Any]:
    permit = _permit(session, permit_id)
    if move == "send-back" and not (body.reason and body.reason.strip()):
        raise ApiError(422, "invalid_input", "Please say why the permit goes back.")
    if move == "sign":
        readiness = permit_readiness(session, permit)
        if readiness["crew_status"] == "unscored":
            raise conflict(
                "The crew has not been scored yet. Ask the planner to run the evening score first."
            )
        if readiness["crew_status"] == "red":
            raise conflict(
                f"The crew has {readiness['open_reassignments']} open reassign today "
                "recommendation(s). The planner must settle them before this permit can be signed."
            )
        drafts = session.scalars(
            select(PermitCondition).where(
                PermitCondition.permit_id == permit.id,
                PermitCondition.status == ConditionStatus.DRAFT,
            )
        ).all()
        if drafts:
            raise conflict("Accept, edit or reject the drafted conditions before signing.")
    try:
        transition(session, permit, move, user, body.reason)
    except InvalidMove as error:
        raise conflict(str(error)) from None
    session.commit()
    return {"id": permit.id, "status": permit.status.value}
