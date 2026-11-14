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
from app.engine.score import ScoreResult, score
from app.engine.weights import Weights
from app.models import Activity, Assignment, PersonCompetency, SwapProposal
from app.models.scores import ConditionsSource, SwapStatus, Tier

TIER_RANK = {Tier.FIT: 0, Tier.FIT_WITH_CONTROLS: 1, Tier.REASSIGN: 2}


@dataclass(frozen=True)
class Candidate:
    activity_id: int
    r: float
    tier: Tier


def candidate_activities(session: Session, assignment: Assignment) -> list[int]:
    current = session.get_one(Activity, assignment.activity_id)
    held = set(
        session.scalars(
            select(PersonCompetency.competency_id).where(
                PersonCompetency.person_id == assignment.person_id
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
) -> Candidate:
    """Score the worker as if moved, without keeping the change."""
    original = assignment.activity_id
    with session.begin_nested() as savepoint:
        assignment.activity_id = activity_id
        session.flush()
        result = score(session, assignment.id, weights, source)
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
) -> list[SwapProposal]:
    proposals: list[SwapProposal] = []
    for result in sorted(scores, key=lambda s: s.r, reverse=True):
        if len(proposals) >= PLANNER_LIMIT:
            break
        if result.tier != Tier.REASSIGN:
            continue
        assignment = session.get_one(Assignment, result.assignment_id)
        alternative = session.get_one(Activity, assignment.activity_id).lower_hazard_alternative_id
        best: Candidate | None = None
        for activity_id in candidate_activities(session, assignment):
            candidate = evaluate(session, assignment, activity_id, weights, source)
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
            status=SwapStatus.PROPOSED,
            reason=f"Move to {target.name.lower()}: relative risk {result.r:.2f} to {best.r:.2f}",
        )
        session.add(proposal)
        proposals.append(proposal)
    session.flush()
    return proposals
