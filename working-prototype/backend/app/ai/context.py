"""What the copilot may see when it writes for a person, and the role boundary for questions.

Every section of context is tagged with the data scope it needs (policy/access.py). Only
the sections the person's role may see are built at all, so the model never receives
data the person could not open themselves.
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.decisions import Choice, Predicate, decide
from app.ai.drafts import get_or_draft
from app.audit import audit
from app.clock import site_now
from app.engine.run import evening_shift, latest_run
from app.models import (
    Activity,
    Assignment,
    AssignmentScore,
    AuditEntry,
    FitnessOutcome,
    Gang,
    LabPanel,
    Observation,
    Permit,
    Person,
    Role,
    ScoreRun,
    Shift,
    SwapProposal,
    WarningRecord,
    Zone,
)
from app.models.ai import AiDraft
from app.models.records import ObservationKind
from app.models.scores import SwapStatus, Tier
from app.models.warnings import WarningStatus
from app.policy.access import ACCESS, DataScope, can
from app.views.readiness import permit_readiness

ALTERNATIVE_FLOOR = 0.2  # an in-role data area this likely to answer is good enough

SCOPE_WORDS: dict[str, str] = {
    "own_profile": "your own profile",
    "own_health": "your own health record",
    "crew_actions": "actions for a crew",
    "site_tiers": "readiness tiers, tier counts and work reasons for the site's workers on a shift",
    "swap_proposals": "reassignment proposals",
    "fitness_outcomes": "fitness outcomes the workers chose to share",
    "permit_counts": "permit readiness counts",
    "aggregates": "site-wide totals of open warnings and safety reports",
    "all_records": "the full safety records",
    "health_detail": "health detail such as lab results",
    "district_aggregates": "district totals",
    "employer_aggregates": "employer totals",
    "audit_redacted": "the audit trail",
    "admin": "people and site administration",
}


def focus_shift(session: Session) -> Shift | None:
    """The shift the latest engine run looked at; before any run, the one the evening run
    will score; failing that, the next shift to start."""
    run = session.scalars(select(ScoreRun).order_by(ScoreRun.id.desc())).first()
    if run is not None:
        return session.get(Shift, run.shift_id)
    return (
        evening_shift(session)
        or session.scalars(
            select(Shift).where(Shift.start_at >= site_now(session)).order_by(Shift.start_at)
        ).first()
    )


def _shift_label(shift: Shift) -> str:
    return f"{shift.kind.value} shift on {shift.date:%d %B}"


def _site_tiers(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    shift = focus_shift(session)
    if shift is None:
        return {"note": "No shift scored yet"}
    run = latest_run(session, shift.id)
    if run is None:
        return {"shift": _shift_label(shift), "note": "Not scored yet"}
    rows = session.execute(
        select(AssignmentScore, Person, Activity)
        .join(Assignment, Assignment.id == AssignmentScore.assignment_id)
        .join(Person, Person.id == Assignment.person_id)
        .join(Activity, Activity.id == Assignment.activity_id)
        .where(AssignmentScore.run_id == run.id)
    ).all()
    counts = Counter(s.tier.value for s, _, _ in rows)
    top = sorted((r for r in rows if r[0].tier == Tier.REASSIGN), key=lambda r: -r[0].r)[:3]
    return {
        "shift": _shift_label(shift),
        "tier_counts": dict(counts),
        "reassign_recommendations": [
            {
                "worker": f"{p.first_name} {p.last_name}",
                "activity": a.name,
                "relative_risk": round(s.r, 2),
                "reason": next(
                    (d["reason"] for d in s.drivers_json if d.get("name") == "reason"), ""
                ),
            }
            for s, p, a in top
        ],
    }


def _swap_proposals(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    rows = session.execute(
        select(SwapProposal, Person, Activity)
        .join(Assignment, Assignment.id == SwapProposal.assignment_id)
        .join(Person, Person.id == Assignment.person_id)
        .join(Activity, Activity.id == SwapProposal.to_activity_id)
        .where(SwapProposal.status.in_([SwapStatus.PROPOSED, SwapStatus.ACCEPTED]))
    ).all()
    return {
        "pending": [
            {
                "worker": f"{p.first_name} {p.last_name}",
                "to": a.name,
                "status": sp.status.value,
                "reason": sp.reason,
            }
            for sp, p, a in rows
        ]
    }


def _permit_counts(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    if subject is not None:
        permit = session.get_one(Permit, subject)
        return {"permit": permit.number, **permit_readiness(session, permit)}
    shift = focus_shift(session)
    if shift is None:
        return {"permits": []}
    permits = session.scalars(select(Permit).where(Permit.shift_id == shift.id)).all()
    return {
        "shift": _shift_label(shift),
        "permits": [
            {"permit": p.number, "status": p.status.value, **permit_readiness(session, p)}
            for p in permits
        ],
    }


def _fitness_outcomes(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    since = site_now(session) - timedelta(days=30)
    rows = session.execute(
        select(FitnessOutcome, Person)
        .join(Person, Person.id == FitnessOutcome.person_id)
        .where(FitnessOutcome.at >= since)
    ).all()
    return {
        "recent": [
            {
                "worker": f"{p.first_name} {p.last_name}",
                "outcome": o.outcome.value if o.share_with_employer else "not shared",
            }
            for o, p in rows
        ]
    }


def _aggregates(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    now = site_now(session)
    warnings = session.execute(
        select(WarningRecord, Zone)
        .join(Zone, Zone.id == WarningRecord.zone_id)
        .where(WarningRecord.status == WarningStatus.OPEN)
    ).all()
    unsafe = session.scalar(
        select(func.count())
        .select_from(Observation)
        .where(Observation.kind != ObservationKind.SAFE, Observation.at >= now - timedelta(days=7))
    )
    return {
        "open_warnings": [
            {"zone": z.name, "level": w.level.value, "opened": w.opened_at.isoformat()}
            for w, z in warnings
        ],
        "unsafe_reports_last_7_days": unsafe,
    }


def _all_records(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    return {"note": "Full records are available on their own screens."}


def _health_detail(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    since = site_now(session) - timedelta(days=120)
    flagged = session.execute(
        select(LabPanel.person_id, func.count())
        .where(LabPanel.flag.is_not(None), LabPanel.at >= since)
        .group_by(LabPanel.person_id)
    ).all()
    refer = _tier_people(session, Tier.REFER)
    return {"workers_with_flagged_labs": len(flagged), "refer_list": refer}


def _tier_people(session: Session, tier: Tier) -> list[str]:
    shift = focus_shift(session)
    run = latest_run(session, shift.id) if shift else None
    if run is None:
        return []
    return [
        f"{p.first_name} {p.last_name}"
        for (p,) in session.execute(
            select(Person)
            .join(Assignment, Assignment.person_id == Person.id)
            .join(AssignmentScore, AssignmentScore.assignment_id == Assignment.id)
            .where(AssignmentScore.run_id == run.id, AssignmentScore.tier == tier)
        )
    ]


def _own_profile(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    row = session.execute(
        select(AssignmentScore, Shift)
        .join(Assignment, Assignment.id == AssignmentScore.assignment_id)
        .join(Shift, Shift.id == Assignment.shift_id)
        .where(Assignment.person_id == user.id)
        .order_by(AssignmentScore.id.desc())
    ).first()
    if row is None:
        return {"name": user.first_name, "job": user.job_title}
    score, shift = row
    return {
        "name": user.first_name,
        "job": user.job_title,
        "next_shift": _shift_label(shift),
        "tier": score.tier.value,
        "reason": next((d["reason"] for d in score.drivers_json if d.get("name") == "reason"), ""),
    }


def _own_health(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    outcome = session.scalars(
        select(FitnessOutcome)
        .where(FitnessOutcome.person_id == user.id)
        .order_by(FitnessOutcome.at.desc())
    ).first()
    return {"latest_outcome": outcome.outcome.value if outcome else None}


def _crew_actions(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    gangs = session.scalars(select(Gang).where(Gang.foreman_id == user.id)).all()
    return {"gangs": [g.name for g in gangs], "note": "Actions only; no answers or results."}


def _district(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    return {"note": "District totals of 10 or more, by zone."}


def _employer(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    return {"note": "Employer totals of 10 or more."}


def _audit(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    rows = session.execute(
        select(AuditEntry.action, func.count()).group_by(AuditEntry.action)
    ).all()
    return {"actions": dict(rows)}


def _admin(session: Session, user: Person, subject: int | None) -> dict[str, Any]:
    rows = session.execute(select(Person.role, func.count()).group_by(Person.role)).all()
    return {"people_by_role": {r.value: n for r, n in rows}}


BUILDERS: dict[str, Callable[[Session, Person, int | None], dict[str, Any]]] = {
    "site_tiers": _site_tiers,
    "swap_proposals": _swap_proposals,
    "permit_counts": _permit_counts,
    "fitness_outcomes": _fitness_outcomes,
    "aggregates": _aggregates,
    "all_records": _all_records,
    "health_detail": _health_detail,
    "own_profile": _own_profile,
    "own_health": _own_health,
    "crew_actions": _crew_actions,
    "district_aggregates": _district,
    "employer_aggregates": _employer,
    "audit_redacted": _audit,
    "admin": _admin,
}

KIND_SCOPES: dict[str, tuple[str, ...] | None] = {
    "brief": None,  # every scope the role has
    "permit": ("permit_counts",),
    "question_answer": None,
}


def build_context(
    session: Session, user: Person, kind: str, subject: int | None = None
) -> dict[str, Any]:
    wanted = KIND_SCOPES.get(kind)
    scopes = [s for s in ACCESS[user.role] if wanted is None or s in wanted]
    context: dict[str, Any] = {"role": user.role.value, "site_time": site_now(session).isoformat()}
    for scope in sorted(scopes):
        context[scope] = BUILDERS[scope](session, user, subject)
    return context


@dataclass
class QuestionReply:
    text: str
    declined: bool
    draft: AiDraft | None
    scopes_needed: list[str]
    note: str = ""


def answer_question(session: Session, user: Person, text: str) -> QuestionReply:
    """Answer from the person's own scopes; decline at the role boundary, before writing."""
    entry = audit(session, user, "question_asked", "question", "-", evidence={"length": len(text)})
    questions = [
        Choice(
            "data_needed",
            "Which ONE kind of data is essential to answer this question?",
            [(scope, SCOPE_WORDS[scope]) for scope in BUILDERS],
        ),
        Predicate(
            "needs_health_detail",
            "Does answering need individual health data such as lab results, diagnoses or "
            "the reason someone visited the clinic?",
        ),
    ]
    decision = decide(session, "question", entry.id, text, questions)
    note = ""
    if decision is None:
        needed: list[str] = []
        note = "The boundary check was not available, so this answer uses only your own data."
    else:
        primary = decision.choice("data_needed")
        needed = [primary] if primary in BUILDERS else []
        if primary in BUILDERS and not can(user.role, primary):  # type: ignore[arg-type]
            # Decline only if nothing this role can see is a plausible source.
            options = decision.probabilities("data_needed")
            own = [s for s in options if s in BUILDERS and can(user.role, s)]  # type: ignore[arg-type]
            best = max(own, key=lambda s: options[s], default=None)
            if best is not None and options[best] >= ALTERNATIVE_FLOOR:
                needed = [best]
        if (
            decision.probability("needs_health_detail") or 0
        ) >= 0.5 and "health_detail" not in needed:
            needed.append("health_detail")
    outside = [s for s in needed if not can(user.role, s)]  # type: ignore[arg-type]
    if outside:
        words = ", ".join(SCOPE_WORDS[s] for s in outside)
        audit(
            session,
            user,
            "question_declined",
            "question",
            str(entry.id),
            evidence={"outside": outside},
        )
        return QuestionReply(
            text=(
                f"I can't answer that for your role. It needs {words}, "
                "which your role does not see."
            ),
            declined=True,
            draft=None,
            scopes_needed=needed,
        )
    context = build_context(session, user, "question_answer")
    context["question"] = text
    draft = get_or_draft(
        session, "question_answer", "question", entry.id, context, actor_id=user.id
    )
    return QuestionReply(
        text=draft.content, declined=False, draft=draft, scopes_needed=needed, note=note
    )


__all__ = ["DataScope", "Role", "answer_question", "build_context", "focus_shift"]
