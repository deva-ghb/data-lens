"""Early warnings: the site view, the ten-step record, drafting and confirming each step,
conditions into permits, closing with an outcome, and the district view."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.ai.context import focus_shift
from app.ai.drafts import get_or_draft
from app.api.common import (
    LOCAL,
    SessionDep,
    UserDep,
    conflict,
    draft_out,
    not_found,
    person_name,
    require_role,
    require_scope,
)
from app.audit import audit
from app.clock import site_now
from app.detector.detect import detect, evaluate_zone
from app.detector.open_record import STEP_NAMES, open_warning
from app.detector.series import clear_feed_index, feed_index
from app.engine.learn import propose_weights_from_outcomes
from app.errors import ApiError
from app.models import (
    Action,
    AiDraft,
    Assignment,
    ClinicVisit,
    Inspection,
    Permit,
    PermitCondition,
    Person,
    Role,
    WarningRecord,
    WarningStep,
    Zone,
)
from app.models.ai import AiDraftStatus
from app.models.permits import ConditionOrigin, ConditionStatus
from app.models.warnings import WarningLevel, WarningOutcome, WarningStatus, WarningStepStatus
from app.policy.suppression import Cell, small_cell_threshold, suppress

router = APIRouter(tags=["warnings"])
CONFIRMER = {
    1: "hse_head",
    2: "hse_head",
    3: "hse_head",
    4: "hse_head",
    5: "hse_head",
    6: "foreman",
    7: "hse_head",
    8: "permit_issuer",
    9: "hse_head",
    10: "system",
}
AI_LINKED = {2, 3}
PERMIT_CONDITIONS = [
    "Start the first lift after the deck WBGT falls below 32 C.",
    "Work-rest cycle 45 minutes on, 15 minutes off in the shade for crew from the affected camp block.",
    "Buddy pairs on every lashing platform above the second tier.",
    "Suspend if deck WBGT stays over 32 C for 30 minutes.",
]


def _record(session, warning_id: int) -> WarningRecord:  # type: ignore[no-untyped-def]
    record = session.get(WarningRecord, warning_id)
    if record is None:
        raise not_found("warning")
    return record


def _summary(session, w: WarningRecord) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    zone = session.get_one(Zone, w.zone_id)
    drafted = session.scalar(
        select(func.count())
        .select_from(WarningStep)
        .where(WarningStep.warning_id == w.id, WarningStep.status == WarningStepStatus.DRAFTED)
    )
    confirmed = session.scalar(
        select(func.count())
        .select_from(WarningStep)
        .where(WarningStep.warning_id == w.id, WarningStep.status == WarningStepStatus.CONFIRMED)
    )
    return {
        "id": w.id,
        "zone": zone.name,
        "level": w.level.value,
        "status": w.status.value,
        "outcome": w.outcome.value if w.outcome else None,
        "opened_at": w.opened_at.isoformat(),
        "closed_at": w.closed_at.isoformat() if w.closed_at else None,
        "classes": (w.evidence_json or {}).get("classes", []),
        "steps_drafted": drafted,
        "steps_confirmed": confirmed,
    }


def _detector_day(session):  # type: ignore[no-untyped-def]
    return (site_now(session) + LOCAL).date() - timedelta(days=1)


@router.get("/warnings")
def warnings(
    session: SessionDep, user: Person = Depends(require_role("hse_head"))
) -> dict[str, Any]:
    day = _detector_day(session)
    index = feed_index(session)
    zones = []
    for zone in session.scalars(select(Zone).order_by(Zone.kind, Zone.name)):
        evaluation = evaluate_zone(session, zone.id, day, index=index)
        zones.append(
            {
                "zone": zone.name,
                "kind": zone.kind.value,
                "level": evaluation.level.value if evaluation.level else "normal",
                "index": evaluation.index,
                "classes": sorted(evaluation.classes_agreeing),
                "late_feeds": evaluation.late_feeds,
            }
        )
    records = session.scalars(select(WarningRecord).order_by(WarningRecord.opened_at.desc())).all()
    return {
        "day": day.isoformat(),
        "zones": zones,
        "open": [_summary(session, w) for w in records if w.status == WarningStatus.OPEN],
        "closed": [_summary(session, w) for w in records if w.status == WarningStatus.CLOSED],
    }


@router.post("/warnings/scan")
def scan(session: SessionDep, user: Person = Depends(require_role("hse_head"))) -> dict[str, Any]:
    clear_feed_index(session)
    day = _detector_day(session)
    opened = []
    # One open record per district episode, the same rule the back-test and the seed use.
    zones = {z.id: z for z in session.scalars(select(Zone))}

    def district_of(zone_id: int) -> int:
        z = zones[zone_id]
        return z.parent_id or z.id

    open_districts = {
        district_of(zid)
        for zid in session.scalars(
            select(WarningRecord.zone_id).where(WarningRecord.status == WarningStatus.OPEN)
        )
    }
    for signal in detect(session, day):
        if signal.level not in (WarningLevel.WARNING, WarningLevel.ALERT):
            continue
        if district_of(signal.zone_id) in open_districts:
            continue
        opened.append(open_warning(session, signal, user).id)
        open_districts.add(district_of(signal.zone_id))
    session.commit()
    return {"day": day.isoformat(), "opened": opened}


def _affected_permits(session, record: WarningRecord) -> list[Permit]:  # type: ignore[no-untyped-def]
    shift = focus_shift(session)
    if shift is None:
        return []
    zone = session.get_one(Zone, record.zone_id)
    residents = set(session.scalars(select(Person.id).where(Person.camp_zone_id == zone.id)))
    out = []
    for permit in session.scalars(select(Permit).where(Permit.shift_id == shift.id)):
        crew = set(
            session.scalars(
                select(Assignment.person_id).where(
                    Assignment.shift_id == permit.shift_id,
                    Assignment.activity_id == permit.activity_id,
                    Assignment.zone_id == permit.zone_id,
                )
            )
        )
        if permit.zone_id == zone.id or crew & residents:
            out.append(permit)
    return out


def _step_out(session, step: WarningStep) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    draft = session.get(AiDraft, step.draft_id) if step.draft_id else None
    return {
        "step": step.step,
        "name": STEP_NAMES[step.step - 1],
        "status": step.status.value,
        "confirmer_role": CONFIRMER[step.step],
        "linked_by_ai": step.step in AI_LINKED,
        "draft": draft_out(session, draft, step.confirmed_by),
        "confirmed_by": person_name(session, step.confirmed_by),
        "confirmed_at": step.confirmed_at.isoformat() if step.confirmed_at else None,
    }


@router.get("/warnings/{warning_id}")
def record(warning_id: int, session: SessionDep, user: UserDep) -> dict[str, Any]:
    if user.role not in (Role.HSE_HEAD, Role.PERMIT_ISSUER, Role.FOREMAN):
        raise ApiError(403, "forbidden", "Warning records are not available for your role.")
    w = _record(session, warning_id)
    steps = session.scalars(
        select(WarningStep).where(WarningStep.warning_id == w.id).order_by(WarningStep.step)
    ).all()
    permits = _affected_permits(session, w)
    actions = session.scalars(
        select(Action).where(Action.source_kind == "warning", Action.source_id == w.id)
    ).all()
    inspections = session.scalars(
        select(Inspection).where(Inspection.source_kind == "warning", Inspection.source_id == w.id)
    ).all()
    return {
        **_summary(session, w),
        "evidence": w.evidence_json,
        "steps": [_step_out(session, s) for s in steps],
        "permits_affected": [
            {"id": p.id, "number": p.number, "status": p.status.value} for p in permits
        ],
        "actions": [
            {
                "id": a.id,
                "title": a.title,
                "status": a.status.value,
                "control_level": a.control_level.value,
            }
            for a in actions
        ],
        "inspections": [
            {"id": i.id, "status": i.status.value, "due_at": i.due_at.isoformat()}
            for i in inspections
        ],
        "verification": (w.evidence_json or {}).get("verification"),
    }


class DraftBody(BaseModel):
    refresh: bool = False


def _context(session, w: WarningRecord, n: int) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    zone = session.get_one(Zone, w.zone_id)
    steps = session.scalars(
        select(WarningStep).where(WarningStep.warning_id == w.id).order_by(WarningStep.step)
    ).all()
    confirmed = {}
    for s in steps:
        if s.status == WarningStepStatus.CONFIRMED and s.draft_id:
            confirmed[STEP_NAMES[s.step - 1]] = session.get_one(AiDraft, s.draft_id).content
    earlier = [
        {
            "zone": session.get_one(Zone, r.zone_id).name,
            "opened": r.opened_at.isoformat(),
            "outcome": r.outcome.value if r.outcome else None,
        }
        for r in session.scalars(
            select(WarningRecord).where(
                WarningRecord.id != w.id, WarningRecord.status == WarningStatus.CLOSED
            )
        )
    ]
    return {
        "step": STEP_NAMES[n - 1],
        "zone": zone.name,
        "opened_at": w.opened_at.isoformat(),
        "evidence": w.evidence_json,
        "earlier_records": earlier,
        "permits_affected": [p.number for p in _affected_permits(session, w)],
        "confirmed_sections": confirmed,
    }


@router.post("/warnings/{warning_id}/steps/{n}/draft")
def draft_step(
    warning_id: int,
    n: int,
    body: DraftBody,
    session: SessionDep,
    user: Person = Depends(require_role("hse_head")),
) -> dict[str, Any]:
    w = _record(session, warning_id)
    if w.status != WarningStatus.OPEN:
        raise conflict("This warning is closed.")
    if not 1 <= n <= 10:
        raise not_found("step")
    step = session.scalars(
        select(WarningStep).where(WarningStep.warning_id == w.id, WarningStep.step == n)
    ).one()
    if step.status == WarningStepStatus.CONFIRMED:
        raise conflict("This section is already confirmed.")
    draft = get_or_draft(
        session,
        f"warning_step_{n}",
        "warning",
        w.id,
        _context(session, w, n),
        actor_id=user.id,
        fresh=body.refresh,
    )
    if draft.id is not None:
        step.draft_id = draft.id
        step.status = WarningStepStatus.DRAFTED
    session.commit()
    return (
        _step_out(session, step)
        if draft.id is not None
        else {**_step_out(session, step), "draft": draft_out(session, draft)}
    )


class ConfirmBody(BaseModel):
    content: str


@router.post("/warnings/{warning_id}/steps/{n}/confirm")
def confirm_step(
    warning_id: int, n: int, body: ConfirmBody, session: SessionDep, user: UserDep
) -> dict[str, Any]:
    w = _record(session, warning_id)
    if w.status != WarningStatus.OPEN:
        raise conflict("This warning is closed.")
    role = CONFIRMER.get(n)
    allowed = {
        "hse_head": {Role.HSE_HEAD},
        "permit_issuer": {Role.PERMIT_ISSUER},
        "foreman": {Role.FOREMAN, Role.HSE_HEAD},
    }.get(role or "", set())
    if user.role not in allowed:
        raise ApiError(
            403,
            "forbidden",
            f"Step {n} is confirmed by the {(role or 'system').replace('_', ' ')}.",
        )
    if not body.content.strip():
        raise ApiError(422, "invalid_input", "The section needs some text.")
    step = session.scalars(
        select(WarningStep).where(WarningStep.warning_id == w.id, WarningStep.step == n)
    ).one()
    if step.status == WarningStepStatus.CONFIRMED:
        raise conflict("This section is already confirmed.")
    draft = session.get(AiDraft, step.draft_id) if step.draft_id else None
    if draft is None:
        draft = AiDraft(
            kind=f"warning_step_{n}",
            subject_kind="warning",
            subject_id=w.id,
            language="en",
            prompt_version="manual",
            model="person",
            deployment="person",
            content=body.content.strip(),
            sure_json=[],
            unsure_json=[],
            would_change_json=[],
            confidence=1.0,
            reasoning_json={"evidence": [], "rules": [], "inferences": [], "rejected": []},
            status=AiDraftStatus.CONFIRMED,
            created_at=site_now(session),
        )
        session.add(draft)
        session.flush()
        step.draft_id = draft.id
    else:
        draft.content = body.content.strip()
        draft.status = AiDraftStatus.CONFIRMED
    step.status = WarningStepStatus.CONFIRMED
    step.confirmed_by = user.id
    step.confirmed_at = site_now(session)
    if n == 8:
        for permit in _affected_permits(session, w):
            for text in PERMIT_CONDITIONS:
                exists = session.scalar(
                    select(PermitCondition.id).where(
                        PermitCondition.permit_id == permit.id,
                        PermitCondition.warning_id == w.id,
                        PermitCondition.text == text,
                    )
                )
                if exists is None:
                    session.add(
                        PermitCondition(
                            permit_id=permit.id,
                            text=text,
                            origin=ConditionOrigin.WARNING,
                            warning_id=w.id,
                            status=ConditionStatus.DRAFT,
                        )
                    )
    if n == 9:
        _learning_from(session, w, draft.content)
    audit(session, user, "warning_step_confirmed", "warning", str(w.id), evidence={"step": n})
    session.commit()
    return _step_out(session, step)


class CloseBody(BaseModel):
    outcome: str | None = None


@router.post("/warnings/{warning_id}/close")
def close(
    warning_id: int,
    body: CloseBody,
    session: SessionDep,
    user: Person = Depends(require_role("hse_head")),
) -> dict[str, Any]:
    w = _record(session, warning_id)
    if w.status == WarningStatus.CLOSED:
        raise conflict("This warning is already closed.")
    try:
        outcome = WarningOutcome(body.outcome or "")
    except ValueError:
        raise ApiError(
            422, "invalid_input", "Choose an outcome: right, early, false alarm or missed."
        ) from None
    w.status = WarningStatus.CLOSED
    w.outcome = outcome
    w.closed_at = site_now(session)
    step = session.scalars(
        select(WarningStep).where(WarningStep.warning_id == w.id, WarningStep.step == 10)
    ).one()
    step.status = WarningStepStatus.CONFIRMED
    step.confirmed_at = w.closed_at
    audit(
        session, user, "warning_closed", "warning", str(w.id), evidence={"outcome": outcome.value}
    )
    proposal = propose_weights_from_outcomes(session)
    session.commit()
    return {**_summary(session, w), "weights_proposed": proposal.version if proposal else None}


SYNDROMES = ["heat", "respiratory", "gastro", "injury", "musculoskeletal"]


@router.get("/district")
def district(
    session: SessionDep, user: Person = Depends(require_scope("district_aggregates", "aggregates"))
) -> dict[str, Any]:
    now = site_now(session)
    k = small_cell_threshold(session)
    since = now - timedelta(days=28)
    village = session.scalars(select(Zone).where(Zone.name == "Mirsal Village District")).one()
    zones = [
        z
        for z in session.scalars(
            select(Zone).where(Zone.parent_id == village.id).order_by(Zone.name)
        )
    ] + [village]
    rows = []
    for syndrome in SYNDROMES:
        cells = []
        for z in zones:
            n = session.scalar(
                select(func.count())
                .select_from(ClinicVisit)
                .where(
                    ClinicVisit.zone_id == z.id,
                    ClinicVisit.syndrome == syndrome,
                    ClinicVisit.at >= since,
                    ClinicVisit.at <= now,
                )
            )
            cells.append(Cell("Unlocated" if z.id == village.id else z.name, n or 0))
        table = suppress(cells, k)
        rows.append(
            {
                "syndrome": syndrome,
                "cells": [{"zone": c.label, "value": c.value} for c in table.cells],
                "total": table.total,
            }
        )
    return {
        "district": village.name,
        "period_days": 28,
        "threshold": k,
        "columns": [c["zone"] for c in rows[0]["cells"]],
        "rows": rows,
    }


def _learning_from(session, w: WarningRecord, content: str) -> None:  # type: ignore[no-untyped-def]
    """Step 9 confirmed: a card, a toolbox talk and a practice change wait for the HSE head
    to share. They are written only from the confirmed sections."""
    from app.models import LearningItem
    from app.models.learning import LearningKind, LearningStatus

    for kind, draft_kind in (
        (LearningKind.CARD, "learning_card"),
        (LearningKind.TOOLBOX_TALK, "toolbox_talk"),
        (LearningKind.SWP_CHANGE, "swp_change"),
    ):
        exists = session.scalar(
            select(LearningItem.id).where(
                LearningItem.source_kind == "warning",
                LearningItem.source_id == w.id,
                LearningItem.kind == kind,
            )
        )
        if exists is not None:
            continue
        item = LearningItem(
            kind=kind, source_kind="warning", source_id=w.id, status=LearningStatus.DRAFT
        )
        session.add(item)
        session.flush()
        text = AiDraft(
            kind=draft_kind,
            subject_kind="learning",
            subject_id=item.id,
            language="en",
            prompt_version="from-step-9",
            model="person",
            deployment="person",
            content=content,
            sure_json=[],
            unsure_json=[],
            would_change_json=[],
            confidence=1.0,
            reasoning_json={"evidence": [], "rules": [], "inferences": [], "rejected": []},
            status=AiDraftStatus.CONFIRMED,
            created_at=site_now(session),
        )
        session.add(text)
        session.flush()
        item.draft_id = text.id
