"""Incidents, near misses and hazard reports from a phone, and targeted inspections.

A report is saved first, whatever happens next. Then the Decisions API triages it (type,
potential severity, likelihood, photo checks) and the copilot drafts the record. If the
AI is unavailable the report stands and a person writes the record by hand. A confirmed
record counts toward the activity's control history.
"""

import base64
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.decisions import Choice, Predicate, Score, decide
from app.ai.drafts import get_or_draft, stored_draft
from app.api.common import (
    SessionDep,
    UserDep,
    conflict,
    draft_out,
    not_found,
    person_name,
    require_scope,
)
from app.audit import audit
from app.clock import site_now
from app.db import BACKEND_DIR
from app.errors import ApiError
from app.models import (
    Activity,
    AiDecision,
    AiDraft,
    HazardReport,
    Incident,
    Inspection,
    InspectionCheck,
    NearMiss,
    Person,
    Role,
    WarningRecord,
    Zone,
)
from app.models.actions import CheckResult, InspectionStatus
from app.models.ai import AiDraftStatus
from app.models.records import IncidentKind, RecordStatus
from app.models.roster import ShiftKind

router = APIRouter(tags=["incidents"])
MEDIA = BACKEND_DIR / "data" / "media"
KINDS = {"near_miss": NearMiss, "incident": Incident, "hazard": HazardReport}
LEVELS = [
    ("1", "Minor"),
    ("2", "Moderate"),
    ("3", "Serious"),
    ("4", "Major"),
    ("5", "Fatal or life changing"),
]
LIKELIHOOD = [
    ("1", "Rare"),
    ("2", "Unlikely"),
    ("3", "Possible"),
    ("4", "Likely"),
    ("5", "Almost certain"),
]
PHOTO_CHECKS = {
    "harness_not_clipped": "Does the photo show someone working at height without the harness clipped on?",
    "person_under_load": "Does the photo show a person under a suspended load?",
    "missing_ppe": "Does the photo show someone without a hard hat or high-visibility vest?",
}


class ReportBody(BaseModel):
    text: str
    zone: str
    activity_code: str | None = None
    photo: str | None = None  # a data URL from the phone camera


def _save_photo(data_url: str) -> str:
    header, _, payload = data_url.partition(",")
    if not header.startswith("data:image/") or not payload:
        raise ApiError(422, "invalid_input", "The photo could not be read.")
    ext = "png" if "png" in header else "jpg"
    MEDIA.mkdir(parents=True, exist_ok=True)
    key = f"{uuid.uuid4().hex}.{ext}"
    (MEDIA / key).write_bytes(base64.b64decode(payload))
    return key


def _triage(session, kind: str, record_id: int, text: str, photo: str | None):  # type: ignore[no-untyped-def]
    questions: list = [
        Choice(
            "report_type",
            "What kind of event does this report describe?",
            [
                ("near_miss", "Nobody hurt, but it could have been"),
                ("injury", "Someone was hurt"),
                ("property", "Damage only"),
                ("environment", "A spill or release"),
                ("hazard", "A condition to fix, nothing happened"),
            ],
        ),
        Score(
            "potential_severity", "If things had gone wrong, how bad could it have been?", LEVELS
        ),
        Score(
            "likelihood", "How likely is a repeat in the next month if nothing changes?", LIKELIHOOD
        ),
    ]
    content: Any = text
    if photo:
        questions += [Predicate(name, q) for name, q in PHOTO_CHECKS.items()]
        content = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": text},
                    {"type": "input_image", "image_url": photo},
                ],
            }
        ]
    return decide(session, kind, record_id, content, questions)


@router.post("/incidents", status_code=201)
def report(body: ReportBody, session: SessionDep, user: UserDep) -> dict[str, Any]:
    if user.role in (Role.AUTHORITY, Role.ADMIN):
        raise ApiError(403, "forbidden", "Reports come from people on site.")
    text = body.text.strip()
    if len(text) < 5:
        raise ApiError(422, "invalid_input", "Say in a few words what happened.")
    zone = session.scalars(select(Zone).where(Zone.name == body.zone)).first()
    if zone is None:
        raise not_found("zone")
    activity = (
        session.scalars(select(Activity).where(Activity.code == body.activity_code)).first()
        if body.activity_code
        else None
    )
    photo_key = _save_photo(body.photo) if body.photo else None
    now = site_now(session)
    shift_kind = ShiftKind.NIGHT if (now.hour >= 15 or now.hour < 3) else ShiftKind.DAY
    record: Any
    if activity is not None:
        record = NearMiss(
            activity_id=activity.id,
            zone_id=zone.id,
            reported_by=user.id,
            at=now,
            shift_kind=shift_kind,
            text=text,
            potential_severity=3,
            status=RecordStatus.OPEN,
            photo_key=photo_key,
        )
        kind = "near_miss"
    else:
        record = HazardReport(
            activity_id=None,
            zone_id=zone.id,
            reported_by=user.id,
            at=now,
            text=text,
            status=RecordStatus.OPEN,
            photo_key=photo_key,
        )
        kind = "hazard"
    session.add(record)
    session.flush()
    audit(
        session, user, "report_submitted", kind, str(record.id), evidence={"photo": bool(photo_key)}
    )
    session.commit()
    decision = _triage(session, kind, record.id, text, body.photo)
    if decision is not None:
        level = decision.level("potential_severity")
        if kind == "near_miss" and level is not None:
            record.potential_severity = max(1, min(5, round(level)))
        if decision.choice("report_type") == "injury" and activity is not None:
            # Someone was hurt: it is an incident, not a near miss.
            session.delete(record)
            session.flush()
            record = Incident(
                activity_id=activity.id,
                zone_id=zone.id,
                reported_by=user.id,
                at=now,
                shift_kind=shift_kind,
                kind=IncidentKind.INJURY,
                text=text,
                photo_key=photo_key,
                potential_severity=max(1, min(5, round(level or 3))),
                status=RecordStatus.OPEN,
            )
            session.add(record)
            session.flush()
            kind = "incident"
            session.get_one(AiDecision, decision.record_id).subject_kind = "incident"
            session.get_one(AiDecision, decision.record_id).subject_id = record.id
    context = {
        "report": text,
        "zone": zone.name,
        "activity": activity.name if activity else None,
        "triage": decision.answers if decision else None,
    }
    get_or_draft(session, "incident_record", kind, record.id, context, actor_id=user.id)
    session.commit()
    return {
        "kind": kind,
        "id": record.id,
        "status": record.status.value,
        "has_photo": bool(photo_key),
    }


def _get(session, kind: str, record_id: int):  # type: ignore[no-untyped-def]
    model = KINDS.get(kind)
    record = session.get(model, record_id) if model else None
    if record is None:
        raise not_found("report")
    return record


def _decision(session, kind: str, record_id: int) -> AiDecision | None:  # type: ignore[no-untyped-def]
    return session.scalars(
        select(AiDecision)
        .where(AiDecision.subject_kind == kind, AiDecision.subject_id == record_id)
        .order_by(AiDecision.id.desc())
    ).first()


def _risk(decision: AiDecision | None) -> dict[str, int] | None:
    if decision is None:
        return None
    answers = {a["name"]: a for a in decision.answers_json}
    sev = answers.get("potential_severity", {}).get("score")
    lik = answers.get("likelihood", {}).get("score")
    if sev is None or lik is None:
        return None
    s, l_ = max(1, min(5, round(sev + 1))), max(1, min(5, round(lik + 1)))
    return {"likelihood": l_, "severity": s, "score": s * l_}


@router.get("/incidents")
def reports(
    session: SessionDep, user: Person = Depends(require_scope("all_records", "aggregates"))
) -> list[dict[str, Any]]:
    out = []
    for kind, model in KINDS.items():
        for r in session.scalars(select(model).order_by(model.at.desc()).limit(80)):
            zone = session.get_one(Zone, r.zone_id)
            out.append(
                {
                    "kind": kind,
                    "id": r.id,
                    "at": r.at.isoformat(),
                    "zone": zone.name,
                    "text": r.text,
                    "status": r.status.value,
                    "potential": getattr(r, "potential_severity", None),
                    "has_photo": bool(getattr(r, "photo_key", None)),
                }
            )
    return sorted(out, key=lambda r: r["at"], reverse=True)


@router.get("/incidents/{kind}/{record_id}")
def report_detail(
    kind: str,
    record_id: int,
    session: SessionDep,
    user: Person = Depends(require_scope("all_records", "aggregates")),
) -> dict[str, Any]:
    r = _get(session, kind, record_id)
    decision = _decision(session, kind, record_id)
    answers = {a["name"]: a for a in decision.answers_json} if decision else {}
    draft = stored_draft(session, "incident_record", kind, record_id)
    zone = session.get_one(Zone, r.zone_id)
    activity = session.get(Activity, r.activity_id) if getattr(r, "activity_id", None) else None
    return {
        "kind": kind,
        "id": r.id,
        "at": r.at.isoformat(),
        "zone": zone.name,
        "activity": activity.name if activity else None,
        "text": r.text,
        "status": r.status.value,
        "reported_by": person_name(session, getattr(r, "reported_by", None)),
        "photo_url": f"/api/media/{r.photo_key}" if getattr(r, "photo_key", None) else None,
        "triage": {
            "type": answers.get("report_type", {}).get("choice"),
            "type_confidence": answers.get("report_type", {}).get("confidence"),
        }
        if decision
        else None,
        "photo_checks": {n: answers[n].get("probability") for n in PHOTO_CHECKS if n in answers},
        "risk": _risk(decision),
        "record": draft_out(session, draft)
        or {
            "status": "unavailable",
            "content": "",
            "sure": [],
            "unsure": [],
            "would_change": [],
            "confidence": 0,
            "id": "",
            "kind": "incident_record",
            "reasoning": {"evidence": [], "rules": [], "inferences": [], "rejected": []},
        },
    }


class ConfirmBody(BaseModel):
    content: str
    kind: str | None = None


@router.post("/incidents/{kind}/{record_id}/confirm")
def confirm(
    kind: str,
    record_id: int,
    body: ConfirmBody,
    session: SessionDep,
    user: Person = Depends(require_scope("all_records")),
) -> dict[str, Any]:
    r = _get(session, kind, record_id)
    if r.status == RecordStatus.CLOSED:
        raise conflict("This record is already confirmed.")
    if not body.content.strip():
        raise ApiError(422, "invalid_input", "The record needs some text.")
    draft = stored_draft(session, "incident_record", kind, record_id)
    if draft is None:
        draft = AiDraft(
            kind="incident_record",
            subject_kind=kind,
            subject_id=record_id,
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
    else:
        draft.content = body.content.strip()
        draft.status = AiDraftStatus.CONFIRMED
    r.status = RecordStatus.CLOSED
    if isinstance(r, Incident):
        r.closed_at = site_now(session)
    audit(session, user, "report_confirmed", kind, str(record_id))
    session.commit()
    return {"kind": kind, "id": record_id, "status": r.status.value}


@router.get("/media/{key}")
def media(key: str, user: UserDep) -> FileResponse:
    path = (MEDIA / key).resolve()
    if path.parent != MEDIA.resolve() or not path.exists():
        raise not_found("photo")
    return FileResponse(Path(path))


# --- inspections --------------------------------------------------------------------------


def _inspection_out(session, inspection: Inspection) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    checks = session.scalars(
        select(InspectionCheck)
        .where(InspectionCheck.inspection_id == inspection.id)
        .order_by(InspectionCheck.id)
    ).all()
    return {
        "id": inspection.id,
        "status": inspection.status.value,
        "due_at": inspection.due_at.isoformat(),
        "zone": session.get_one(Zone, inspection.zone_id).name,
        "source_kind": inspection.source_kind,
        "source_id": inspection.source_id,
        "checks": [
            {
                "id": c.id,
                "driver": c.driver,
                "question": c.question,
                "result": c.result.value if c.result else None,
                "note": c.note,
            }
            for c in checks
        ],
    }


QUESTIONS = {
    "cooling_units_down": "Walk the block: how many room cooling units are off, and in which rooms?",
    "heat_visits": "Ask the clinic: are today's heat visits from this block still above usual?",
    "tickets_opened": "Check the camp operator's open fault list for this block.",
    "absent": "Ask the foremen: who is off sick this week and why (no health detail)?",
    "unsafe_reports": "Walk the work area at the busiest hour: are the controls in the safe working practice holding?",
    "tired": "At shift start, ask the crew how they slept and who is on a fourth night.",
    "short_sleep": "Check rest rooms and roster changes that cut sleep.",
    "pm10": "Check cab windows and mask use on the yard at 14:00.",
}


@router.post("/warnings/{warning_id}/inspection", status_code=201)
def build_inspection(
    warning_id: int, session: SessionDep, user: Person = Depends(require_scope("aggregates"))
) -> dict[str, Any]:
    w = session.get(WarningRecord, warning_id)
    if w is None:
        raise not_found("warning")
    from datetime import timedelta

    inspection = Inspection(
        source_kind="warning",
        source_id=w.id,
        zone_id=w.zone_id,
        due_at=site_now(session) + timedelta(hours=6),
        status=InspectionStatus.SCHEDULED,
    )
    session.add(inspection)
    session.flush()
    for signal in (w.evidence_json or {}).get("signals", []):
        session.add(
            InspectionCheck(
                inspection_id=inspection.id,
                driver=signal["metric"],
                question=QUESTIONS.get(
                    signal["metric"], f"Check what drives {signal['metric']} on the ground."
                ),
            )
        )
    session.add(
        InspectionCheck(
            inspection_id=inspection.id,
            driver="water_points",
            question="Are water points full within 30 metres of every crew?",
        )
    )
    audit(session, user, "inspection_created", "warning", str(w.id))
    session.commit()
    return _inspection_out(session, inspection)


@router.get("/inspections")
def inspections(
    session: SessionDep, user: Person = Depends(require_scope("aggregates", "crew_actions"))
) -> list[dict[str, Any]]:
    return [
        _inspection_out(session, i)
        for i in session.scalars(select(Inspection).order_by(Inspection.due_at.desc()))
    ]


class CheckBody(BaseModel):
    result: str
    note: str | None = None


@router.post("/inspections/{inspection_id}/checks/{check_id}")
def record_check(
    inspection_id: int,
    check_id: int,
    body: CheckBody,
    session: SessionDep,
    user: Person = Depends(require_scope("aggregates", "crew_actions")),
) -> dict[str, Any]:
    check = session.get(InspectionCheck, check_id)
    if check is None or check.inspection_id != inspection_id:
        raise not_found("check")
    try:
        check.result = CheckResult(body.result)
    except ValueError:
        raise ApiError(422, "invalid_input", "The result is confirmed or not found.") from None
    check.note = (body.note or "").strip() or None
    confirms = None
    if check.note:
        decision = decide(
            session,
            "inspection_check",
            check.id,
            check.note,
            [
                Predicate(
                    "confirms",
                    f"Does this note confirm the problem the check looked for: {check.question}",
                )
            ],
        )
        confirms = decision.probability("confirms") if decision else None
    inspection = session.get_one(Inspection, inspection_id)
    checks = session.scalars(
        select(InspectionCheck).where(InspectionCheck.inspection_id == inspection_id)
    ).all()
    if all(c.result is not None for c in checks):
        inspection.status = InspectionStatus.DONE
    if inspection.source_kind == "warning":
        w = session.get_one(WarningRecord, inspection.source_id)
        evidence = dict(w.evidence_json or {})
        evidence["verification"] = {
            "confirmed": sum(1 for c in checks if c.result == CheckResult.CONFIRMED),
            "not_found": sum(1 for c in checks if c.result == CheckResult.NOT_FOUND),
            "total": len(checks),
        }
        w.evidence_json = evidence
    audit(
        session,
        user,
        "inspection_check",
        "inspection",
        str(inspection_id),
        evidence={"check": check.id, "result": body.result},
    )
    session.commit()
    return {
        "id": check.id,
        "result": check.result.value,
        "note": check.note,
        "note_confirms": confirms,
    }
