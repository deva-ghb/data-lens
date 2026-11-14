"""The readiness vector: six dimensions per worker per shift.

Each dimension gives a multiplier (1.0 means no shortfall), a deficit from 0 to 1,
a confidence, how fresh its evidence is, where it came from, and a reason written in
work terms. Reasons never mention lab results or a diagnosis; the planner sees them.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import site_now
from app.engine.groups import group_rates, memberships
from app.engine.weights import Weights
from app.models import (
    Absence,
    Activity,
    ActivityHazard,
    Assignment,
    CheckIn,
    Competency,
    FitnessOutcome,
    Hazard,
    LabPanel,
    Person,
    PersonCompetency,
    Shift,
    TrainingRecord,
    UnwellEvent,
)
from app.models.health import FitnessDecision
from app.models.roster import Feeling, ShiftKind

DIMENSIONS = ("fatigue", "heat_strain", "physical", "acute", "safety_behaviour", "competency")
SHORT_SLEEP = ("under_5", "5_to_6")
REFRESHER_FOR_HAZARD = {"FALL_HEIGHT": ("HEIGHT_REFRESHER", 365)}
DRIVING_COMPETENCIES = {"TT_DRIVER", "REACH_STACKER"}


@dataclass(frozen=True)
class ReadinessInputs:
    person_id: int
    consecutive_nights: int
    acclimatisation_days: int
    short_sleep_checkins_last10: int
    latest_checkin: CheckIn | None
    competencies_current: set[str]
    training_missing: set[str]
    group_code: str | None
    group_multiplier: float
    fitness_outcome: FitnessOutcome | None
    lab_flags: int
    unwell_event: bool
    activity_competency: str | None = None
    not_today: bool = False


@dataclass(frozen=True)
class Factor:
    multiplier: float
    deficit: float
    confidence: float
    freshness_hours: float | None
    source: str
    reason: str


def knowledge_time(session: Session, shift: Shift, live: bool = False) -> datetime:
    """The latest moment whose records the engine may read for a shift.

    The evening run looks ahead: it may know nothing after the site clock or the shift
    start, whichever comes first. A shift-start or manual re-score reads everything up to
    the site clock, so late check-ins and "I feel unwell" during the shift are seen.
    """
    now = site_now(session)
    return now if live else min(now, shift.start_at)


def _consecutive_nights(session: Session, person_id: int, shift: Shift) -> int:
    if shift.kind != ShiftKind.NIGHT:
        return 0
    nights = set(
        session.scalars(
            select(Shift.date)
            .join(Assignment, Assignment.shift_id == Shift.id)
            .where(
                Assignment.person_id == person_id,
                Shift.kind == ShiftKind.NIGHT,
                Shift.date <= shift.date,
                Shift.date > shift.date - timedelta(days=14),
            )
        )
    )
    # Nights worked, not just rostered: a night off sick breaks the run.
    nights -= set(
        session.scalars(
            select(Absence.date).where(
                Absence.person_id == person_id,
                Absence.date <= shift.date,
                Absence.date > shift.date - timedelta(days=14),
            )
        )
    )
    count, day = 0, shift.date
    while day in nights:
        count += 1
        day -= timedelta(days=1)
    return count


def required_refreshers(session: Session, activity_id: int) -> dict[str, int]:
    """Refresher courses an activity needs, with how many days each stays current."""
    hazards = session.scalars(
        select(Hazard.code)
        .join(ActivityHazard, ActivityHazard.hazard_id == Hazard.id)
        .where(ActivityHazard.activity_id == activity_id)
    ).all()
    needed = dict(REFRESHER_FOR_HAZARD[h] for h in hazards if h in REFRESHER_FOR_HAZARD)
    competency = session.scalar(
        select(Competency.code)
        .join(Activity, Activity.competency_id == Competency.id)
        .where(Activity.id == activity_id)
    )
    if competency in DRIVING_COMPETENCIES:
        needed["DRIVING_REFRESHER"] = 548
    return needed


def gather_inputs(
    session: Session, person_id: int, shift_id: int, as_of: datetime | None = None
) -> ReadinessInputs:
    shift = session.get_one(Shift, shift_id)
    person = session.get_one(Person, person_id)
    as_of = as_of or knowledge_time(session, shift)
    assignment = session.scalars(
        select(Assignment).where(Assignment.person_id == person_id, Assignment.shift_id == shift_id)
    ).first()

    recent = session.scalars(
        select(CheckIn)
        .where(CheckIn.person_id == person_id, CheckIn.at < as_of)
        .order_by(CheckIn.at.desc())
        .limit(10)
    ).all()
    this_shift = session.scalars(
        select(CheckIn).where(
            CheckIn.person_id == person_id, CheckIn.shift_id == shift_id, CheckIn.at <= as_of
        )
    ).first()

    competencies = set(
        session.scalars(
            select(Competency.code)
            .join(PersonCompetency, PersonCompetency.competency_id == Competency.id)
            .where(PersonCompetency.person_id == person_id)
            .where(
                (PersonCompetency.valid_until.is_(None))
                | (PersonCompetency.valid_until >= shift.date)
            )
        )
    )
    missing: set[str] = set()
    activity_competency = None
    if assignment is not None:
        activity_competency = session.scalar(
            select(Competency.code)
            .join(Activity, Activity.competency_id == Competency.id)
            .where(Activity.id == assignment.activity_id)
        )
        for course, valid_days in required_refreshers(session, assignment.activity_id).items():
            last = session.scalar(
                select(TrainingRecord.completed_on)
                .where(
                    TrainingRecord.person_id == person_id,
                    TrainingRecord.course_code == course,
                    TrainingRecord.completed_on <= shift.date,
                )
                .order_by(TrainingRecord.completed_on.desc())
            )
            if last is None or (shift.date - last).days > valid_days:
                missing.add(course)

    group = memberships(session, shift.start_at).get(person_id)
    rates = group_rates(session, shift.start_at)
    multiplier = rates[group].multiplier if group in rates else 1.0

    outcome = session.scalars(
        select(FitnessOutcome)
        .where(
            FitnessOutcome.person_id == person_id,
            FitnessOutcome.at <= as_of,
            FitnessOutcome.at > as_of - timedelta(days=30),
        )
        .order_by(FitnessOutcome.at.desc())
    ).first()
    # "Not today" covers the shift it was given for: anything starting within 24 hours.
    not_today = (
        outcome is not None
        and outcome.outcome == FitnessDecision.NOT_TODAY
        and shift.start_at - outcome.at <= timedelta(hours=24)
    )
    flags_since = outcome.at if outcome else as_of - timedelta(days=120)
    lab_flags = len(
        session.scalars(
            select(LabPanel.id).where(
                LabPanel.person_id == person_id,
                LabPanel.flag.is_not(None),
                LabPanel.at > max(flags_since, as_of - timedelta(days=120)),
                LabPanel.at <= as_of,
            )
        ).all()
    )
    unwell = (
        session.scalar(
            select(UnwellEvent.id).where(
                UnwellEvent.person_id == person_id,
                UnwellEvent.shift_id == shift_id,
                UnwellEvent.at <= as_of,
            )
        )
        is not None
    )
    return ReadinessInputs(
        person_id=person_id,
        consecutive_nights=_consecutive_nights(session, person_id, shift),
        acclimatisation_days=(shift.date - person.site_arrival_date).days,
        short_sleep_checkins_last10=sum(1 for c in recent if c.sleep_hours_band in SHORT_SLEEP),
        latest_checkin=this_shift,
        competencies_current=competencies,
        training_missing=missing,
        group_code=group,
        group_multiplier=multiplier,
        fitness_outcome=outcome,
        lab_flags=lab_flags,
        unwell_event=unwell,
        activity_competency=activity_competency,
        not_today=not_today,
    )


def _factor(
    multiplier: float,
    weights: Weights,
    *,
    confidence: float,
    freshness: float | None,
    source: str,
    reason: str,
) -> Factor:
    cap = weights.factor_caps["factor"]
    m = round(min(max(multiplier, 0.5), cap), 4)
    deficit = max(0.0, min((m - 1.0) / (cap - 1.0), 1.0))
    return Factor(m, round(deficit, 3), confidence, freshness, source, reason)


def _ordinal(n: int) -> str:
    return {1: "first", 2: "second", 3: "third", 4: "fourth"}.get(n, f"{n}th")


def readiness(inputs: ReadinessInputs, weights: Weights) -> dict[str, Factor]:
    checkin = inputs.latest_checkin
    factors: dict[str, Factor] = {}

    nights = inputs.consecutive_nights
    fatigue = weights.fatigue_for_nights(nights) * (
        1 + weights.short_sleep_step * inputs.short_sleep_checkins_last10
    )
    parts = []
    if nights >= 2:
        parts.append(f"{_ordinal(nights).capitalize()} night in a row")
    if inputs.short_sleep_checkins_last10:
        parts.append(
            f"short sleep in {inputs.short_sleep_checkins_last10} of the last 10 check-ins"
        )
    factors["fatigue"] = _factor(
        fatigue,
        weights,
        confidence=0.9,
        freshness=0.0,
        source="Roster and check-ins",
        reason="; ".join(parts) if parts else "Rested on the current rotation",
    )

    days = inputs.acclimatisation_days
    if days < 7:
        heat, heat_reason = (
            weights.heat_strain["acclimatisation_under_7_days"],
            (f"On site {days} days; not yet used to the heat"),
        )
    elif days < 14:
        heat, heat_reason = (
            weights.heat_strain["acclimatisation_under_14_days"],
            (f"On site {days} days; still getting used to the heat"),
        )
    else:
        heat, heat_reason = 1.0, "Used to working in the heat"
    factors["heat_strain"] = _factor(
        heat, weights, confidence=0.95, freshness=None, source="HR records", reason=heat_reason
    )

    # Only an outcome the worker chose to share can change the score. Lab results never
    # change it directly; two or more flags send the worker to the clinician (Refer).
    physical, physical_reason = 1.0, "No restriction on record"
    outcome = inputs.fitness_outcome
    if (
        outcome is not None
        and outcome.share_with_employer
        and outcome.outcome == FitnessDecision.FIT_WITH_RESTRICTIONS
    ):
        physical = weights.physical["fit_with_restrictions"]
        physical_reason = "Cleared by the clinician with restrictions"
    factors["physical"] = _factor(
        physical,
        weights,
        confidence=0.8,
        freshness=None,
        source="Clinic outcome",
        reason=physical_reason,
    )

    if checkin is None:
        factors["acute"] = _factor(
            1.0,
            weights,
            confidence=0.5,
            freshness=None,
            source="Check-in",
            reason="No check-in yet for this shift",
        )
    else:
        acute, acute_parts = 1.0, []
        if checkin.feeling == Feeling.TIRED:
            acute *= weights.acute["tired"]
            acute_parts.append("Reported feeling tired at check-in")
        if not checkin.hydration_ok:
            acute *= weights.acute["hydration_low"]
            acute_parts.append("Not enough water before the shift")
        factors["acute"] = _factor(
            acute,
            weights,
            confidence=0.9,
            freshness=0.0,
            source="Check-in",
            reason="; ".join(acute_parts) or "Checked in feeling fine",
        )

    group = inputs.group_multiplier
    factors["safety_behaviour"] = _factor(
        min(group, weights.group_cap),
        weights,
        confidence=0.85,
        freshness=24.0,
        source="Safety records (group rate)",
        reason=(
            "Training path and tenure share a higher unsafe-act rate on this work"
            if group > 1.05
            else "Training path and tenure share a lower unsafe-act rate on this work"
            if group < 0.95
            else "Training path and tenure in line with the site"
        ),
    )

    competency, comp_reason = 1.0, "Training and competencies current"
    if inputs.activity_competency and inputs.activity_competency not in inputs.competencies_current:
        competency = weights.competency["competency_expired"]
        comp_reason = "Competency for this work has expired"
    elif inputs.training_missing:
        competency = weights.competency["refresher_missing"]
        names = {"HEIGHT_REFRESHER": "height refresher", "DRIVING_REFRESHER": "driving refresher"}
        missing = ", ".join(names.get(c, c.lower()) for c in sorted(inputs.training_missing))
        comp_reason = f"{missing.capitalize()} not done"
    factors["competency"] = _factor(
        competency,
        weights,
        confidence=0.95,
        freshness=None,
        source="Training records",
        reason=comp_reason,
    )
    return factors
