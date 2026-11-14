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
    if not 1 <= limit <= 1000:
        raise ApiError(422, "invalid_input", "Ask for between 1 and 1,000 entries.")
    query = select(AuditEntry).order_by(AuditEntry.id.desc()).limit(limit)
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


# --- settings: small-cell threshold, autonomy, weights ------------------------------------

from pydantic import BaseModel  # noqa: E402

from app.api.common import SessionDep as _S  # noqa: E402
from app.api.common import require_scope  # noqa: E402
from app.audit import audit  # noqa: E402
from app.engine.learn import approve_weights  # noqa: E402
from app.models import Setting, WeightsVersion  # noqa: E402
from app.policy.access import ACCESS  # noqa: E402
from app.policy.suppression import THRESHOLD_KEY, small_cell_threshold  # noqa: E402

AUTONOMY_ACTIONS = {
    "raise_warning": ("Raise an early warning", False),
    "draft_message": ("Draft a message to a crew", False),
    "change_work_rest": ("Change a work-rest cycle", False),
    "reassign_worker": ("Reassign a worker", True),
    "sign_permit": ("Sign a permit", True),
    "health_restriction": ("Restrict on health grounds", True),
}
MODES = ("tell_me", "draft_it", "do_and_tell")
DEFAULT_AUTONOMY = {
    "raise_warning": "do_and_tell",
    "draft_message": "draft_it",
    "change_work_rest": "draft_it",
    "reassign_worker": "draft_it",
    "sign_permit": "tell_me",
    "health_restriction": "tell_me",
}
EMPLOYMENT_LINE = [
    "A tier lasts one shift and cannot be exported.",
    "Tiers have no connection to HR systems.",
    "Tiers are never used for hiring, discipline, pay, performance, contract renewal or sponsorship.",
    "A reassignment is not recorded against the worker, and every reassignment can be contested.",
    "The clinician has the final word on health.",
]


def _autonomy(session) -> dict[str, str]:  # type: ignore[no-untyped-def]
    row = session.get(Setting, "autonomy")
    return {**DEFAULT_AUTONOMY, **(row.value if row else {})}


def _settings_writer(user: UserDep) -> Person:
    if user.role not in (Role.HSE_HEAD, Role.ADMIN):
        raise ApiError(
            403, "forbidden", "Only the HSE head or the admin changes governance settings."
        )
    return user


@router.get("/governance")
def governance(
    session: _S, user: Person = Depends(require_scope("aggregates", "admin", "audit_redacted"))
) -> dict[str, Any]:
    autonomy = _autonomy(session)
    weights = session.scalars(select(WeightsVersion).order_by(WeightsVersion.id)).all()
    return {
        "matrix": {role.value: sorted(scopes) for role, scopes in ACCESS.items()},
        "threshold": small_cell_threshold(session),
        "autonomy": [
            {"action": k, "label": label, "locked": locked, "mode": autonomy[k]}
            for k, (label, locked) in AUTONOMY_ACTIONS.items()
        ],
        "employment_line": EMPLOYMENT_LINE,
        "weights": [
            {
                "id": w.id,
                "version": w.version,
                "status": w.status.value,
                "note": w.body_json.get("note"),
                "approved_at": w.approved_at.isoformat() if w.approved_at else None,
            }
            for w in weights
        ],
    }


class ThresholdBody(BaseModel):
    value: int


@router.put("/governance/threshold")
def set_threshold(
    body: ThresholdBody, session: _S, user: Person = Depends(_settings_writer)
) -> dict[str, Any]:
    if not 5 <= body.value <= 50:
        raise ApiError(422, "invalid_input", "The threshold must be between 5 and 50.")
    before = small_cell_threshold(session)
    row = session.get(Setting, THRESHOLD_KEY)
    if row is None:
        session.add(Setting(key=THRESHOLD_KEY, value=body.value))
    else:
        row.value = body.value
    audit(
        session,
        user,
        "threshold_changed",
        "setting",
        THRESHOLD_KEY,
        evidence={"from": before, "to": body.value},
    )
    session.commit()
    return {"threshold": body.value}


class AutonomyBody(BaseModel):
    action: str
    mode: str


@router.put("/governance/autonomy")
def set_autonomy(
    body: AutonomyBody, session: _S, user: Person = Depends(_settings_writer)
) -> dict[str, Any]:
    if body.action not in AUTONOMY_ACTIONS or body.mode not in MODES:
        raise ApiError(422, "invalid_input", "Unknown action or mode.")
    if AUTONOMY_ACTIONS[body.action][1] and body.mode == "do_and_tell":
        raise ApiError(
            409,
            "conflict",
            "This decision is locked to people. The copilot can draft it, never do it.",
        )
    autonomy = _autonomy(session)
    autonomy[body.action] = body.mode
    row = session.get(Setting, "autonomy")
    if row is None:
        session.add(Setting(key="autonomy", value=autonomy))
    else:
        row.value = autonomy
    audit(session, user, "autonomy_changed", "setting", body.action, evidence={"mode": body.mode})
    session.commit()
    return {"action": body.action, "mode": body.mode}


@router.post("/governance/weights/{version_id}/approve")
def approve(
    version_id: int, session: _S, user: Person = Depends(_settings_writer)
) -> dict[str, Any]:
    try:
        w = approve_weights(session, version_id, user)
    except ValueError as error:
        raise ApiError(409, "conflict", str(error)) from None
    session.commit()
    return {"version": w.version, "status": w.status.value}


# --- the Authority: employer aggregates ---------------------------------------------------

from collections import defaultdict  # noqa: E402

from app.ai.context import focus_shift  # noqa: E402
from app.engine.run import latest_run  # noqa: E402
from app.models import Assignment, AssignmentScore, Employer  # noqa: E402
from app.policy.suppression import Cell, suppress  # noqa: E402


@router.get("/authority/employers")
def employers(
    session: _S, user: Person = Depends(require_scope("employer_aggregates", "aggregates"))
) -> dict[str, Any]:
    k = small_cell_threshold(session)
    names = [e.name for e in session.scalars(select(Employer).order_by(Employer.name))]
    shift = focus_shift(session)
    run = latest_run(session, shift.id) if shift else None
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    workers: dict[str, int] = defaultdict(int)
    for (emp_name,) in session.execute(
        select(Employer.name)
        .join(Person, Person.employer_id == Employer.id)
        .where(Person.role == Role.WORKER)
    ):
        workers[emp_name] += 1
    if run is not None:
        for tier, emp_name in session.execute(
            select(AssignmentScore.tier, Employer.name)
            .join(Assignment, Assignment.id == AssignmentScore.assignment_id)
            .join(Person, Person.id == Assignment.person_id)
            .join(Employer, Employer.id == Person.employer_id)
            .where(AssignmentScore.run_id == run.id)
        ):
            counts[tier.value][emp_name] += 1
    rows = [
        {
            "measure": "Workers",
            "cells": [
                {"employer": c.label, "value": c.value}
                for c in suppress([Cell(n, workers[n]) for n in names], k).cells
            ],
            "total": suppress([Cell(n, workers[n]) for n in names], k).total,
        }
    ]
    for tier, label in (
        ("fit_with_controls", "On extra controls next shift"),
        ("reassign", "Reassign today next shift"),
    ):
        table = suppress([Cell(n, counts[tier][n]) for n in names], k)
        rows.append(
            {
                "measure": label,
                "cells": [{"employer": c.label, "value": c.value} for c in table.cells],
                "total": table.total,
            }
        )
    return {"threshold": k, "employers": names, "rows": rows}
