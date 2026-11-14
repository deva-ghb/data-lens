"""Greedy swap proposals for workers in "Reassign today".

Highest R first. Candidates are activities the worker holds the competency for, graded
below the current one; the activity's named
lower-hazard alternative is tried first. The candidate with the lowest resulting R that
improves the tier wins. Proposals stop at the planner's alert budget.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.budget import PLANNER_LIMIT
from app.engine.crew_rules import CrewMember, check_crew_rules
from app.engine.score import ScoreResult, score
from app.engine.weights import Weights
from app.models import Activity, Assignment, PersonCompetency, Shift, SwapProposal
from app.models.scores import ConditionsSource, SwapStatus, Tier

TIER_RANK = {Tier.FIT: 0, Tier.FIT_WITH_CONTROLS: 1, Tier.REASSIGN: 2}


@dataclass(frozen=True)
class Candidate:
    activity_id: int
    r: float
    tier: Tier


def keeps_crew_rules(crew: list[CrewMember], moved_assignment_id: int, heat_tier: int) -> bool:
    """A move is allowed only if the crew it leaves breaks no rule it did not already break."""
    before = {b.rule for b in check_crew_rules(crew, heat_tier)}
    after = {
        b.rule
        for b in check_crew_rules(
            [m for m in crew if m.assignment_id != moved_assignment_id], heat_tier
        )
    }
    return after <= before


def crews_from(scores: list[ScoreResult]) -> dict[tuple[int | None, int], list[CrewMember]]:
    """Scored workers grouped by gang and activity: the crew each crew rule applies to."""
    crews: dict[tuple[int | None, int], list[CrewMember]] = {}
    for s in scores:
        crews.setdefault((s.gang_id, s.activity_id), []).append(
            CrewMember(s.assignment_id, s.tier, s.r, s.acclimatisation_days, s.group_code, s.grade)
        )
    return crews


def candidate_activities(session: Session, assignment: Assignment) -> list[int]:
    current = session.get_one(Activity, assignment.activity_id)
    shift_date = session.get_one(Shift, assignment.shift_id).date
    held = set(
        session.scalars(
            select(PersonCompetency.competency_id).where(
                PersonCompetency.person_id == assignment.person_id,
                (PersonCompetency.valid_until.is_(None))
                | (PersonCompetency.valid_until >= shift_date),
            )
        )
    )
    options = session.scalars(
        select(Activity).where(
            Activity.grade < current.grade,
            Activity.grade >= 1,
            Activity.competency_id.in_(held),
        )
    ).all()
    ordered = sorted(options, key=lambda a: (a.id != current.lower_hazard_alternative_id, -a.grade))
    return [a.id for a in ordered]


def evaluate(
    session: Session,
    assignment: Assignment,
    activity_id: int,
    weights: Weights,
    source: ConditionsSource,
    live: bool = False,
) -> Candidate:
    """Score the worker as if moved, without keeping the change."""
    original = assignment.activity_id
    with session.begin_nested() as savepoint:
        assignment.activity_id = activity_id
        session.flush()
        result = score(session, assignment.id, weights, source, live=live)
        savepoint.rollback()
    assignment.activity_id = original
    if result is None:  # grade 1 or 2 work is not scored per person
        return Candidate(activity_id, 1.0, Tier.FIT)
    return Candidate(activity_id, result.r, result.tier)


def propose_swaps(
    session: Session,
    run_id: int,
    scores: list[ScoreResult],
    weights: Weights,
    source: ConditionsSource = ConditionsSource.SCENARIO,
    live: bool = False,
) -> list[SwapProposal]:
    proposals: list[SwapProposal] = []
    crews = crews_from(scores)
    for result in sorted(scores, key=lambda s: s.r, reverse=True):
        if len(proposals) >= PLANNER_LIMIT:
            break
        if result.tier != Tier.REASSIGN:
            continue
        existing = session.scalars(
            select(SwapProposal.id).where(
                SwapProposal.assignment_id == result.assignment_id,
                SwapProposal.status != SwapStatus.REJECTED,
            )
        ).first()
        if existing is not None:
            continue  # already proposed or decided on an earlier run: never twice
        crew = crews[(result.gang_id, result.activity_id)]
        if not keeps_crew_rules(crew, result.assignment_id, result.heat_tier or 0):
            continue
        assignment = session.get_one(Assignment, result.assignment_id)
        alternative = session.get_one(Activity, assignment.activity_id).lower_hazard_alternative_id
        best: Candidate | None = None
        for activity_id in candidate_activities(session, assignment):
            candidate = evaluate(session, assignment, activity_id, weights, source, live)
            if TIER_RANK.get(candidate.tier, 2) >= TIER_RANK[Tier.REASSIGN]:
                continue
            if best is None or candidate.r < best.r:
                best = candidate
            if activity_id == alternative:
                best = candidate
                break
        if best is None:
            continue
        target = session.get_one(Activity, best.activity_id)
        proposal = SwapProposal(
            run_id=run_id,
            assignment_id=assignment.id,
            to_activity_id=best.activity_id,
            from_activity_id=assignment.activity_id,
            status=SwapStatus.PROPOSED,
            reason=f"Move to {target.name.lower()}: relative risk {result.r:.2f} to {best.r:.2f}",
        )
        session.add(proposal)
        proposals.append(proposal)
        crews[(result.gang_id, result.activity_id)] = [
            m for m in crew if m.assignment_id != result.assignment_id
        ]
    session.flush()
    return proposals
