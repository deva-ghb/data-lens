"""Assignment risk: engine runs, the roster with tiers, the layer build, swaps and approval."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import SessionDep, require_role, require_scope
from app.clock import site_now
from app.engine.run import evening_shift, run_scores
from app.errors import ApiError
from app.models import Person, Shift
from app.models.scores import ConditionsSource, RunKind

router = APIRouter(tags=["assignments"])


class RunBody(BaseModel):
    kind: str = "manual"
    shift_id: int | None = None
    conditions_source: str = "scenario"


@router.post("/runs", status_code=201)
def start_run(
    body: RunBody,
    session: SessionDep,
    user: Person = Depends(require_scope("site_tiers")),
) -> dict[str, Any]:
    try:
        kind = RunKind(body.kind)
        source = ConditionsSource(body.conditions_source)
    except ValueError:
        raise ApiError(422, "invalid_input", "Unknown run kind or conditions source.") from None
    shift = session.get(Shift, body.shift_id) if body.shift_id else default_shift(session, kind)
    if shift is None:
        raise ApiError(404, "not_found", "There is no shift to score.")
    run = run_scores(session, shift.id, kind, source, actor=user)
    session.commit()
    return {"run_id": run.id, "shift_id": shift.id}


def default_shift(session: Session, kind: RunKind) -> Shift | None:
    """The evening run scores tomorrow night's roster; other runs the shift now running,
    or the next one to start."""
    now = site_now(session)
    if kind == RunKind.EVENING:
        return evening_shift(session)
    running = session.scalars(
        select(Shift).where(Shift.start_at <= now, Shift.end_at > now)
    ).first()
    return (
        running
        or session.scalars(
            select(Shift).where(Shift.start_at > now).order_by(Shift.start_at)
        ).first()
    )


# --- the roster, the layer build, swaps --------------------------------------------------

from collections import Counter  # noqa: E402

from app.api.common import conflict, not_found, shift_out  # noqa: E402
from app.audit import audit  # noqa: E402
from app.engine.budget import PLANNER_LIMIT  # noqa: E402
from app.engine.layers import hazards_of  # noqa: E402
from app.engine.montecarlo import split_risk  # noqa: E402
from app.engine.run import crew_breaches, latest_run  # noqa: E402
from app.engine.score import score  # noqa: E402
from app.engine.weights import load_weights  # noqa: E402
from app.models import (  # noqa: E402
    Activity,
    Assignment,
    AssignmentScore,
    Contest,
    Employer,
    Gang,
    SwapProposal,
    Zone,
)
from app.models.roster import AssignmentSource  # noqa: E402
from app.models.scores import SwapStatus  # noqa: E402
from app.policy.tokens import shift_token  # noqa: E402


def _reason(drivers: list[dict[str, Any]]) -> str:
    return next((d.get("reason", "") for d in drivers if d.get("name") == "reason"), "")


def _shift_for_roster(session: Session, shift_id: int | None) -> Shift:
    if shift_id:
        shift = session.get(Shift, shift_id)
    else:
        from app.ai.context import focus_shift

        shift = focus_shift(session)
    if shift is None:
        raise not_found("shift")
    return shift


@router.get("/roster")
def roster(
    session: SessionDep,
    shift_id: int | None = None,
    user: Person = Depends(require_scope("site_tiers")),
) -> dict[str, Any]:
    shift = _shift_for_roster(session, shift_id)
    run = latest_run(session, shift.id)
    rows_q = (
        select(Assignment, Person, Activity, Employer, Gang, Zone)
        .join(Person, Person.id == Assignment.person_id)
        .join(Activity, Activity.id == Assignment.activity_id)
        .join(Employer, Employer.id == Person.employer_id)
        .outerjoin(Gang, Gang.id == Assignment.gang_id)
        .outerjoin(Zone, Zone.id == Assignment.zone_id)
        .where(Assignment.shift_id == shift.id)
    )
    scores = {}
    if run is not None:
        scores = {
            s.assignment_id: s
            for s in session.scalars(
                select(AssignmentScore).where(AssignmentScore.run_id == run.id)
            )
        }
    swaps = {
        sp.assignment_id: sp
        for sp in session.scalars(
            select(SwapProposal)
            .join(Assignment, Assignment.id == SwapProposal.assignment_id)
            .where(Assignment.shift_id == shift.id)
            .order_by(SwapProposal.id)
        )
    }
    activity_names = {a.id: a.name for a in session.scalars(select(Activity))}
    rows = []
    for a, p, act, emp, gang, zone in session.execute(rows_q):
        s = scores.get(a.id)
        sp = swaps.get(a.id)
        contest = None
        if s is not None:
            contest = session.scalars(
                select(Contest).where(Contest.assignment_score_id == s.id)
            ).first()
        rows.append(
            {
                "assignment_id": a.id,
                "worker": f"{p.first_name} {p.last_name}",
                "employer": emp.name,
                "gang": gang.name if gang else None,
                "activity": act.name,
                "grade": act.grade,
                "zone": zone.name if zone else None,
                "source": a.source.value,
                "tier": s.tier.value if s else ("not_scored" if act.grade < 3 else None),
                "r": round(s.r, 2) if s else None,
                "reason": _reason(s.drivers_json) if s else "",
                "confidence": s.confidence if s else None,
                "swap": None
                if sp is None
                else {
                    "id": sp.id,
                    "status": sp.status.value,
                    "to": activity_names[sp.to_activity_id],
                    "reason": sp.reason,
                },
                "contest": None
                if contest is None
                else {"id": contest.id, "status": contest.status.value, "text": contest.text},
            }
        )
    rows.sort(key=lambda r: (-(r["r"] or 0), r["worker"]))
    counts = Counter(r["tier"] for r in rows if r["tier"] and r["tier"] != "not_scored")
    reassign = [r for r in rows if r["tier"] == "reassign"]
    breaches = []
    if run is not None:
        from app.engine.score import ScoreResult

        results = []
        weights = load_weights(session)
        for sid, sc in scores.items():
            asg = session.get_one(Assignment, sid)
            act = session.get_one(Activity, asg.activity_id)
            heat = next((d for d in sc.drivers_json if d.get("name") == "heat"), None)
            tier_num = None
            if heat and "heat tier" in heat.get("reason", ""):
                tier_num = int(heat["reason"].rsplit(" ", 1)[-1])
            results.append(
                ScoreResult(
                    assignment_id=sid,
                    intrinsic=sc.intrinsic,
                    control=sc.control,
                    condition=sc.condition,
                    profile=sc.profile,
                    r=sc.r,
                    tier=sc.tier,
                    drivers=[],
                    confidence=sc.confidence,
                    group_step_limited=sc.group_step_limited,
                    late_feeds=[],
                    reason="",
                    person_id=asg.person_id,
                    activity_id=asg.activity_id,
                    gang_id=asg.gang_id,
                    grade=act.grade,
                    group_code=None,
                    acclimatisation_days=999,
                    heat_tier=tier_num,
                )
            )
        gang_names = {g.id: g.name for g in session.scalars(select(Gang))}
        for b in crew_breaches(results):
            if b["rule"] == "experienced_present":
                continue  # needs group data the planner does not see; checked in the engine run
            breaches.append(
                {
                    **b,
                    "gang": gang_names.get(b["gang_id"]),
                    "activity": activity_names.get(b["activity_id"]),
                }
            )
        assert weights
    return {
        "shift": shift_out(shift),
        "run": None
        if run is None
        else {
            "id": run.id,
            "kind": run.kind.value,
            "ran_at": run.ran_at.isoformat(),
            "conditions_source": run.conditions_source.value,
        },
        "tier_counts": {
            k: counts.get(k, 0)
            for k in ("fit", "fit_with_controls", "reassign", "refer", "unknown")
        },
        "budget": {
            "limit": PLANNER_LIMIT,
            "shown": min(len(reassign), PLANNER_LIMIT),
            "rolled_into_brief": max(len(reassign) - PLANNER_LIMIT, 0),
        },
        "crew_rule_breaches": breaches,
        "rows": rows,
    }


@router.get("/assignments/{assignment_id}/build")
def layer_build(
    assignment_id: int, session: SessionDep, user: Person = Depends(require_scope("site_tiers"))
) -> dict[str, Any]:
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        raise not_found("assignment")
    run = latest_run(session, assignment.shift_id)
    s = None
    if run is not None:
        s = session.scalars(
            select(AssignmentScore).where(
                AssignmentScore.run_id == run.id, AssignmentScore.assignment_id == assignment_id
            )
        ).first()
    if s is None:
        raise not_found("score for that assignment")
    act = session.get_one(Activity, assignment.activity_id)
    person = session.get_one(Person, assignment.person_id)
    weights = load_weights(session)
    # The behavioural group stays inside the score; it is never shown against a name.
    drivers = [
        d
        for d in s.drivers_json
        if d.get("layer") != "summary" and d.get("name") != "safety_behaviour"
    ]
    return {
        "worker": f"{person.first_name} {person.last_name}",
        "activity": act.name,
        "grade": act.grade,
        "hazards": hazards_of(session, act.id),
        "layers": [
            {"name": "intrinsic", "value": s.intrinsic, "drivers": []},
            {
                "name": "control",
                "value": s.control,
                "drivers": [d for d in drivers if d["layer"] == "control"],
            },
            {
                "name": "condition",
                "value": s.condition,
                "drivers": [d for d in drivers if d["layer"] == "condition"],
            },
            {
                "name": "profile",
                "value": s.profile,
                "drivers": [d for d in drivers if d["layer"] == "profile"],
            },
        ],
        "r": round(s.r, 2),
        "tier": s.tier.value,
        "thresholds": list(weights.thresholds[act.grade]),
        "confidence": s.confidence,
        "group_step_limited": s.group_step_limited,
        "reason": _reason(s.drivers_json),
        "late_feeds": next(
            (d.get("late_feeds", []) for d in s.drivers_json if d.get("name") == "reason"), []
        ),
    }


class SwapBody(BaseModel):
    reason: str | None = None


def _swap(session: Session, swap_id: int) -> SwapProposal:
    sp = session.get(SwapProposal, swap_id)
    if sp is None:
        raise not_found("swap")
    return sp


def _move(
    session: Session,
    sp: SwapProposal,
    to: SwapStatus,
    user: Person,
    reason: str | None,
    allowed_from: tuple[SwapStatus, ...],
) -> dict[str, Any]:
    if sp.status not in allowed_from:
        raise conflict(f"This swap is already {sp.status.value.replace('_', ' ')}.")
    sp.status = to
    sp.decided_by = user.id
    if reason:
        sp.reason = f"{sp.reason} | {to.value}: {reason}" if sp.reason else reason
    assignment = session.get_one(Assignment, sp.assignment_id)
    if to == SwapStatus.APPROVED:
        assignment.activity_id = sp.to_activity_id
        assignment.source = AssignmentSource.SWAP
    audit(
        session,
        user,
        f"swap_{to.value}",
        "reassignment",
        shift_token(assignment.person_id, assignment.shift_id),
        evidence={"swap_id": sp.id, "reason": reason} if reason else {"swap_id": sp.id},
    )
    session.commit()
    return {"id": sp.id, "status": sp.status.value}


@router.post("/swaps/{swap_id}/accept")
def accept(
    swap_id: int,
    body: SwapBody,
    session: SessionDep,
    user: Person = Depends(require_role("planner")),
) -> dict[str, Any]:
    return _move(
        session,
        _swap(session, swap_id),
        SwapStatus.ACCEPTED,
        user,
        body.reason,
        (SwapStatus.PROPOSED,),
    )


@router.post("/swaps/{swap_id}/decline")
def decline(
    swap_id: int,
    body: SwapBody,
    session: SessionDep,
    user: Person = Depends(require_role("planner")),
) -> dict[str, Any]:
    if not body.reason or not body.reason.strip():
        raise ApiError(422, "invalid_input", "Please say why you are declining this swap.")
    return _move(
        session,
        _swap(session, swap_id),
        SwapStatus.DECLINED,
        user,
        body.reason.strip(),
        (SwapStatus.PROPOSED, SwapStatus.ACCEPTED),
    )


def _manager(user: Person = Depends(require_scope("swap_proposals"))) -> Person:
    from app.models import Role

    if user.role != Role.SHIFT_MANAGER:
        raise ApiError(403, "forbidden", "Only the shift manager approves a reassignment.")
    return user


@router.post("/swaps/{swap_id}/approve")
def approve(
    swap_id: int, body: SwapBody, session: SessionDep, user: Person = Depends(_manager)
) -> dict[str, Any]:
    return _move(
        session,
        _swap(session, swap_id),
        SwapStatus.APPROVED,
        user,
        body.reason,
        (SwapStatus.ACCEPTED,),
    )


@router.post("/swaps/{swap_id}/reject")
def reject(
    swap_id: int, body: SwapBody, session: SessionDep, user: Person = Depends(_manager)
) -> dict[str, Any]:
    if not body.reason or not body.reason.strip():
        raise ApiError(422, "invalid_input", "Please say why you are rejecting this swap.")
    return _move(
        session,
        _swap(session, swap_id),
        SwapStatus.REJECTED,
        user,
        body.reason.strip(),
        (SwapStatus.ACCEPTED,),
    )


@router.get("/swaps")
def swaps(
    session: SessionDep,
    status: str | None = None,
    user: Person = Depends(require_scope("swap_proposals")),
) -> list[dict[str, Any]]:
    query = (
        select(SwapProposal, Assignment, Person, Activity)
        .join(Assignment, Assignment.id == SwapProposal.assignment_id)
        .join(Person, Person.id == Assignment.person_id)
        .join(Activity, Activity.id == SwapProposal.to_activity_id)
        .order_by(SwapProposal.id.desc())
    )
    if status:
        try:
            wanted = SwapStatus(status)
        except ValueError:
            raise ApiError(422, "invalid_input", "Unknown swap status.") from None
        query = query.where(SwapProposal.status == wanted)
    out = []
    for sp, asg, p, to in session.execute(query):
        current = session.get_one(Activity, sp.from_activity_id or asg.activity_id)
        shift = session.get_one(Shift, asg.shift_id)
        out.append(
            {
                "id": sp.id,
                "status": sp.status.value,
                "worker": f"{p.first_name} {p.last_name}",
                "from": current.name,
                "to": to.name,
                "reason": sp.reason,
                "shift": shift_out(shift),
                "decided_by": None
                if sp.decided_by is None
                else session.get_one(Person, sp.decided_by).first_name,
            }
        )
    return out


@router.get("/risk-split")
def risk_split(
    session: SessionDep, shift_id: int, user: Person = Depends(require_scope("site_tiers"))
) -> dict[str, Any]:
    try:
        result = split_risk(session, shift_id, n=1000)
    except LookupError:
        raise not_found("scored shift") from None
    return {
        "conditions_share": result.conditions_share,
        "crew_share": result.crew_share,
        "total_excess": result.total_expected,
        "p10": result.p10,
        "p90": result.p90,
        "workers": result.workers,
        "peak_wbgt": result.peak_wbgt,
        "forecast_missing": result.forecast_missing,
    }


__all__ = ["router", "score"]


class KeepBody(BaseModel):
    reason: str


@router.post("/assignments/{assignment_id}/keep")
def keep(
    assignment_id: int,
    body: KeepBody,
    session: SessionDep,
    user: Person = Depends(require_role("planner")),
) -> dict[str, Any]:
    """Settle a Reassign today without moving the worker: the planner keeps them on the
    work with extra controls and a logged reason. Covers workers with no proposal too."""
    if user.role.value != "planner":
        raise ApiError(403, "forbidden", "Only the planner settles a reassignment.")
    if not body.reason.strip():
        raise ApiError(422, "invalid_input", "Please say why the worker stays on this work.")
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        raise not_found("assignment")
    proposal = session.scalars(
        select(SwapProposal)
        .where(SwapProposal.assignment_id == assignment_id)
        .order_by(SwapProposal.id.desc())
    ).first()
    if proposal is not None and proposal.status in (SwapStatus.APPROVED, SwapStatus.DECLINED):
        raise conflict("This reassignment is already settled.")
    if proposal is None or proposal.status not in (SwapStatus.PROPOSED, SwapStatus.ACCEPTED):
        run = latest_run(session, assignment.shift_id)
        if run is None:
            raise conflict("Score the shift first.")
        proposal = SwapProposal(
            run_id=run.id,
            assignment_id=assignment_id,
            to_activity_id=assignment.activity_id,
            from_activity_id=assignment.activity_id,
            status=SwapStatus.PROPOSED,
            reason="Kept on the same work with extra controls",
        )
        session.add(proposal)
        session.flush()
    return _move(
        session,
        proposal,
        SwapStatus.DECLINED,
        user,
        body.reason.strip(),
        (SwapStatus.PROPOSED, SwapStatus.ACCEPTED),
    )


class ResolveBody(BaseModel):
    status: str
    note: str | None = None


@router.post("/contests/{contest_id}/resolve")
def resolve_contest(
    contest_id: int,
    body: ResolveBody,
    session: SessionDep,
    user: Person = Depends(require_role("planner")),
) -> dict[str, Any]:
    from app.models.scores import ContestStatus

    contest = session.get(Contest, contest_id)
    if contest is None:
        raise not_found("contest")
    if contest.status != ContestStatus.OPEN:
        raise conflict("This contest is already answered.")
    if body.status not in ("upheld", "dismissed"):
        raise ApiError(422, "invalid_input", "Uphold or dismiss the contest.")
    contest.status = ContestStatus(body.status)
    if body.note and body.note.strip():
        contest.text = f"{contest.text}\n\nPlanner: {body.note.strip()}"
    score_row = session.get_one(AssignmentScore, contest.assignment_score_id)
    assignment = session.get_one(Assignment, score_row.assignment_id)
    audit(
        session,
        user,
        f"contest_{body.status}",
        "reassignment",
        shift_token(assignment.person_id, assignment.shift_id),
    )
    session.commit()
    return {"id": contest.id, "status": contest.status.value}
