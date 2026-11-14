"""Score one assignment: R = Intrinsic x Control x Condition x Profile, then the tier.

Rules that keep the estimate honest:
- every multiplier is capped;
- thresholds depend on the activity's grade; grades 1 and 2 are not scored per person;
- the behavioural group factor can move the tier by at most one step;
- a health signal sends the worker to the clinician (Refer) before anything else;
- at shift start, a worker who has not checked in is Unknown, never Fit.
"""

from dataclasses import dataclass
from math import log
from typing import Any

from sqlalchemy.orm import Session

from app.engine.layers import condition, control, hazards_of, profile
from app.engine.readiness import gather_inputs, knowledge_time, readiness
from app.engine.weights import Weights
from app.models import Activity, Assignment, Shift
from app.models.health import FitnessDecision
from app.models.roster import Feeling
from app.models.scores import ConditionsSource, Tier

ORDER = [Tier.FIT, Tier.FIT_WITH_CONTROLS, Tier.REASSIGN]


@dataclass(frozen=True)
class ScoreResult:
    assignment_id: int
    intrinsic: float
    control: float
    condition: float
    profile: float
    r: float
    tier: Tier
    drivers: list[dict[str, Any]]
    confidence: float
    group_step_limited: bool
    late_feeds: list[str]
    reason: str


def tier_for(grade: int, r: float, weights: Weights) -> Tier:
    low, high = weights.thresholds[grade]
    if r >= high:
        return Tier.REASSIGN
    if r >= low:
        return Tier.FIT_WITH_CONTROLS
    return Tier.FIT


def limit_group_step(with_group: Tier, without_group: Tier) -> tuple[Tier, bool]:
    """The group factor may move the tier one step at most, up or down."""
    a, b = ORDER.index(with_group), ORDER.index(without_group)
    if abs(a - b) <= 1:
        return with_group, False
    return ORDER[b + (1 if a > b else -1)], True


def _contribution(driver: dict[str, Any]) -> float:
    return round(log(driver["multiplier"]), 4) if driver["multiplier"] > 0 else 0.0


def score(
    session: Session,
    assignment_id: int,
    weights: Weights,
    conditions_source: ConditionsSource,
    require_checkin: bool = False,
) -> ScoreResult | None:
    assignment = session.get_one(Assignment, assignment_id)
    activity = session.get_one(Activity, assignment.activity_id)
    if activity.grade < 3:
        return None
    shift = session.get_one(Shift, assignment.shift_id)
    as_of = knowledge_time(session, shift)
    hazards = hazards_of(session, activity.id)

    inputs = gather_inputs(session, assignment.person_id, shift.id)
    factors = readiness(inputs, weights)
    control_layer = control(session, activity.id, shift.start_at, weights)
    condition_layer = condition(
        session, assignment, shift, hazards, weights, conditions_source, as_of
    )
    profile_layer = profile(factors, hazards, weights)
    intrinsic = 1.0
    r = round(intrinsic * control_layer.value * condition_layer.value * profile_layer.value, 4)

    without_group = profile(factors, hazards, weights, without="safety_behaviour")
    r_without = intrinsic * control_layer.value * condition_layer.value * without_group.value
    tier, limited = limit_group_step(
        tier_for(activity.grade, r, weights), tier_for(activity.grade, r_without, weights)
    )

    checkin = inputs.latest_checkin
    outcome = inputs.fitness_outcome
    reason = ""
    if (
        inputs.unwell_event
        or (checkin is not None and checkin.feeling == Feeling.UNWELL)
        or (outcome is not None and outcome.outcome == FitnessDecision.NOT_TODAY)
        or inputs.lab_flags >= 2
    ):
        tier, reason = Tier.REFER, "A health signal needs the clinician first"
    elif outcome is not None and not outcome.share_with_employer:
        tier, reason = Tier.UNKNOWN, "Fitness outcome not shared by the worker"
    elif require_checkin and checkin is None:
        tier, reason = Tier.UNKNOWN, "Has not checked in for this shift"

    drivers = [*control_layer.drivers, *condition_layer.drivers, *profile_layer.drivers]
    for driver in drivers:
        driver["contribution"] = _contribution(driver)
    drivers.sort(key=lambda d: d["contribution"], reverse=True)

    confidence = 0.9
    if checkin is None:
        confidence -= 0.25
    confidence -= 0.1 * len(condition_layer.late_feeds)
    if not reason:
        top = [d["reason"] for d in drivers if d["contribution"] > 0.02][:3]
        reason = "; ".join(top) if top else "Within the activity's demands"

    return ScoreResult(
        assignment_id=assignment.id,
        intrinsic=intrinsic,
        control=control_layer.value,
        condition=condition_layer.value,
        profile=profile_layer.value,
        r=r,
        tier=tier,
        drivers=drivers,
        confidence=round(max(confidence, 0.2), 2),
        group_step_limited=limited,
        late_feeds=condition_layer.late_feeds,
        reason=reason,
    )
