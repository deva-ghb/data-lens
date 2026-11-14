"""The four risk layers that multiply into R.

- Intrinsic: the activity's grade sets the scale and the tier thresholds (value 1.0).
- Control: how well controls held on this activity, from 12 months of unsafe acts,
  behaviours, conditions and near misses per worker-hour, against the site.
- Condition: tomorrow's shift as it will be: heat, night, dust, pace, and how the
  worker's accommodation recovered overnight.
- Profile: the person's readiness vector, weighted by how sensitive the activity is.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.readiness import Factor
from app.engine.weights import Weights
from app.feeds.wbgt import estimate_wbgt, heat_tier
from app.models import (
    Activity,
    ActivityHazard,
    Assignment,
    CampTicket,
    Feed,
    FeedReading,
    Hazard,
    NearMiss,
    Observation,
    Person,
    Shift,
    VesselCall,
    Zone,
)
from app.models.feeds import FeedSource
from app.models.records import ObservationKind
from app.models.roster import ShiftKind
from app.models.scores import ConditionsSource

UABC_KINDS = (
    ObservationKind.UNSAFE_ACT,
    ObservationKind.UNSAFE_BEHAVIOUR,
    ObservationKind.UNSAFE_CONDITION,
)
DUST_ZONE = "Mirsal Port District"
COOLING_UNITS_PER_BLOCK = 40


@dataclass
class LayerResult:
    value: float
    drivers: list[dict[str, Any]] = field(default_factory=list)
    late_feeds: list[str] = field(default_factory=list)


def hazards_of(session: Session, activity_id: int) -> list[str]:
    return list(
        session.scalars(
            select(Hazard.code)
            .join(ActivityHazard, ActivityHazard.hazard_id == Hazard.id)
            .where(ActivityHazard.activity_id == activity_id)
            .order_by(Hazard.code)
        )
    )


def _uabc_by_activity(session: Session, start: datetime, end: datetime) -> dict[int, int]:
    counts: dict[int, int] = {}
    for activity_id, n in session.execute(
        select(Observation.activity_id, func.count())
        .where(Observation.kind.in_(UABC_KINDS), Observation.at >= start, Observation.at < end)
        .group_by(Observation.activity_id)
    ):
        counts[activity_id] = counts.get(activity_id, 0) + n
    for activity_id, n in session.execute(
        select(NearMiss.activity_id, func.count())
        .where(NearMiss.at >= start, NearMiss.at < end)
        .group_by(NearMiss.activity_id)
    ):
        counts[activity_id] = counts.get(activity_id, 0) + n
    return counts


def control_rates(session: Session, at: datetime, weights: Weights) -> dict[int, dict[str, Any]]:
    """Each graded activity's events and rate per 1,000 worker-hours, and the site's."""
    key = ("control_rates", at.date(), weights.id)
    if key in session.info:
        return session.info[key]
    start = datetime(at.year, at.month, at.day) - timedelta(days=weights.control_window_days)
    end = datetime(at.year, at.month, at.day)
    counts = _uabc_by_activity(session, start, end)
    weeks = weights.control_window_days / 7
    activities = session.execute(select(Activity.id, Activity.grade, Activity.exposure_hours_week))
    out: dict[int, dict[str, Any]] = {}
    site_events = site_hours = 0.0
    for activity_id, grade, hours_week in activities:
        hours = hours_week * weeks
        events = counts.get(activity_id, 0)
        out[activity_id] = {"events": events, "hours": hours, "grade": grade}
        if grade >= 3:
            site_events += events
            site_hours += hours
    site_rate = site_events / site_hours * 1000 if site_hours else 0.0
    for row in out.values():
        row["rate"] = row["events"] / row["hours"] * 1000 if row["hours"] else 0.0
        row["site_rate"] = site_rate
    session.info[key] = out
    return out


def control(session: Session, activity_id: int, at: datetime, weights: Weights) -> LayerResult:
    row = control_rates(session, at, weights)[activity_id]
    ratio = row["rate"] / row["site_rate"] if row["site_rate"] else 1.0
    k = weights.control_formula_k
    caps = weights.factor_caps
    value = min(max(1 + k * (ratio - 1), caps["control_min"]), caps["control_max"])
    return LayerResult(
        round(value, 4),
        [
            {
                "layer": "control",
                "name": "control_history",
                "multiplier": round(value, 4),
                "source": "Safety records, last 12 months",
                "freshness_hours": 24.0,
                "reason": (
                    f"{row['events']} unsafe acts, behaviours, conditions and near misses in "
                    f"12 months; {ratio:.2f} times the site rate per hour worked"
                ),
            }
        ],
    )


def _feed_id(session: Session, code: str) -> int:
    return session.scalars(select(Feed.id).where(Feed.code == code)).one()


def peak_wbgt(
    session: Session, start: datetime, end: datetime, source: ConditionsSource
) -> tuple[float | None, datetime | None]:
    """Highest estimated WBGT from the forecast in a window, and when the data was issued."""
    wanted = FeedSource.LIVE if source == ConditionsSource.LIVE else FeedSource.SEEDED
    rows = session.execute(
        select(FeedReading.at, FeedReading.metric, FeedReading.value).where(
            FeedReading.feed_id == _feed_id(session, "WEATHER"),
            FeedReading.zone_id.is_(None),
            FeedReading.source == wanted,
            FeedReading.at >= start,
            FeedReading.at <= end,
        )
    ).all()
    hours: dict[datetime, dict[str, float]] = {}
    for at, metric, value in rows:
        hours.setdefault(at, {})[metric] = value
    best: float | None = None
    for values in hours.values():
        if "temp_c" in values and "rh_pct" in values:
            wbgt = estimate_wbgt(values["temp_c"], values["rh_pct"], values.get("radiation_wm2", 0))
            best = wbgt if best is None else max(best, wbgt)
    latest = max(hours) if hours else None
    return best, latest


def live_window(session: Session) -> tuple[datetime, datetime] | None:
    """The span the live forecast covers, if a live pull has happened."""
    first, last = session.execute(
        select(func.min(FeedReading.at), func.max(FeedReading.at)).where(
            FeedReading.feed_id == _feed_id(session, "WEATHER"),
            FeedReading.source == FeedSource.LIVE,
        )
    ).one()
    return (first, last) if first else None


def condition(
    session: Session,
    assignment: Assignment,
    shift: Shift,
    hazards: list[str],
    weights: Weights,
    source: ConditionsSource,
    as_of: datetime,
) -> LayerResult:
    terms = weights.condition_terms
    result = LayerResult(1.0)
    value = 1.0

    def add(
        name: str, c: float, dimension: str, source_name: str, fresh: float | None, reason: str
    ) -> None:
        nonlocal value
        sens = weights.sensitivity(hazards, dimension)
        effect = 1 + (c - 1) * sens
        value *= effect
        result.drivers.append(
            {
                "layer": "condition",
                "name": name,
                "multiplier": round(effect, 4),
                "source": source_name,
                "freshness_hours": fresh,
                "reason": reason,
            }
        )

    # Heat: the hottest hour from 12 hours before the shift to its end.
    window = (shift.start_at - timedelta(hours=12), shift.end_at)
    if source == ConditionsSource.LIVE:
        span = live_window(session)
        if span is not None:
            window = (span[0], min(span[0] + timedelta(hours=36), span[1]))
    wbgt, issued = peak_wbgt(session, window[0], window[1], source)
    if wbgt is None:
        result.late_feeds.append("Weather forecast")
        add(
            "heat",
            1.0,
            "heat_strain",
            "Weather forecast",
            None,
            "No forecast available; heat not counted",
        )
    else:
        tier = heat_tier(wbgt)
        label = "live forecast" if source == ConditionsSource.LIVE else "forecast"
        add(
            "heat",
            weights.heat_by_tier[tier],
            "heat_strain",
            "Weather forecast (live)" if source == ConditionsSource.LIVE else "Weather forecast",
            0.0 if issued is None else max((as_of - issued).total_seconds() / 3600, 0.0),
            f"Peak WBGT {wbgt:.1f} C in the {label}: heat tier {tier}",
        )

    if shift.kind == ShiftKind.NIGHT:
        add("night", terms["night"]["value"], "fatigue", "Roster", 0.0, "Night shift")

    pm10 = session.scalar(
        select(func.avg(FeedReading.value))
        .join(Zone, Zone.id == FeedReading.zone_id)
        .where(
            FeedReading.feed_id == _feed_id(session, "AIR_QUALITY"),
            Zone.name == DUST_ZONE,
            FeedReading.metric == "pm10",
            FeedReading.at >= min(shift.start_at, as_of) - timedelta(hours=24),
            FeedReading.at <= min(shift.start_at, as_of),
        )
    )
    if pm10 is None:
        result.late_feeds.append("Air quality")
    else:
        dust = 1.0
        for floor, multiplier in terms["dust"]["pm10_steps"]:
            if pm10 >= floor:
                dust = multiplier
        if dust > 1.0:
            add(
                "dust",
                dust,
                "physical",
                "Air quality",
                1.0,
                f"Dusty air: PM10 averaging {pm10:.0f}",
            )

    if assignment.zone_id is not None:
        call = session.scalar(
            select(VesselCall.vessel_name).where(
                VesselCall.berth_zone_id == assignment.zone_id,
                VesselCall.arrives_at < shift.end_at,
                VesselCall.departs_at > shift.start_at,
            )
        )
        if call is not None:
            add(
                "pace",
                terms["pace"]["vessel_call"],
                "safety_behaviour",
                "Terminal plan",
                0.0,
                f"{call} alongside: full working pace",
            )

    person = session.get_one(Person, assignment.person_id)
    if person.camp_zone_id is not None:
        down = session.scalar(
            select(func.coalesce(func.sum(CampTicket.units_affected), 0)).where(
                CampTicket.zone_id == person.camp_zone_id,
                CampTicket.kind == "cooling_failure",
                CampTicket.opened_at <= as_of,
                (CampTicket.closed_at.is_(None)) | (CampTicket.closed_at > as_of),
            )
        )
        if down:
            fraction = down / COOLING_UNITS_PER_BLOCK
            add(
                "camp_recovery",
                1 + terms["camp_recovery"]["per_fraction_down"] * fraction,
                "fatigue",
                "Camp operator tickets",
                1.0,
                f"{down} of {COOLING_UNITS_PER_BLOCK} cooling units down in the camp block",
            )

    result.value = round(min(value, weights.factor_caps["condition"]), 4)
    return result


def profile(
    factors: dict[str, Factor], hazards: list[str], weights: Weights, without: str | None = None
) -> LayerResult:
    value = 1.0
    drivers = []
    for dimension, factor in factors.items():
        if dimension == without:
            continue
        sens = weights.sensitivity(hazards, dimension)
        effect = 1 + (factor.multiplier - 1) * sens
        value *= effect
        drivers.append(
            {
                "layer": "profile",
                "name": dimension,
                "multiplier": round(effect, 4),
                "source": factor.source,
                "freshness_hours": factor.freshness_hours,
                "reason": factor.reason,
            }
        )
    return LayerResult(round(min(value, weights.factor_caps["profile"]), 4), drivers)
