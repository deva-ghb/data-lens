"""Twelve months of safety records: observation cards, near misses, incidents, hazard reports.

The counts are allocated, not sampled, so the computed figures land where the
walkthrough says they do:
- Lashing at height on deck: 11 unsafe acts, 6 unsafe behaviours, 7 unsafe conditions
  and 3 near misses, all on nights. Against the site's rate per worker-hour this gives
  a control multiplier of about 1.15.
- Each behavioural group's unsafe rate per 100 cards on grade 3 to 5 work, relative to
  the site, lands on its multiplier (0.8, 1.6, 1.3, 0.9, 1.4, 1.0).
Closed incidents count toward the control history too (ten of them, none on lashing).
"""

from datetime import datetime, timedelta

from app.models import HazardReport, Incident, NearMiss, Observation
from app.models.records import IncidentKind, ObservationKind, RecordStatus
from app.models.roster import ShiftKind
from seed.context import Ctx
from seed.scenario import CLOCK, HISTORY_START

ACT, BEH, COND, SAFE = (
    ObservationKind.UNSAFE_ACT,
    ObservationKind.UNSAFE_BEHAVIOUR,
    ObservationKind.UNSAFE_CONDITION,
    ObservationKind.SAFE,
)

# Person-linked unsafe cards by cohort: {activity: (acts, behaviours)} and total cards.
GROUP_PLAN: dict[str, tuple[int, dict[str, tuple[int, int]]]] = {
    "exp_inhouse": (50, {"LASH_DECK": (3, 1)}),
    "new_contractor": (50, {"LASH_DECK": (5, 3)}),
    "exp_nights": (38, {"LASH_DECK": (3, 2)}),
    "driver_refreshed": (133, {"TT_DRIVING": (5, 3), "REACH_STACKER": (2, 2)}),
    "driver_overdue": (100, {"TT_DRIVING": (6, 4), "REACH_STACKER": (2, 2)}),
    "mooring": (30, {"MOORING": (2, 1)}),
    "ungrouped": (
        389,
        {
            "QC_OPS": (3, 2),
            "HOLD_CONFINED": (1, 1),
            "HOT_WORK": (1, 1),
            "TWIST_GROUND": (5, 3),
            "REEFER": (3, 1),
            "WORKSHOP_MECH": (4, 2),
            "TT_DRIVING": (3, 1),
            "REACH_STACKER": (2, 0),
        },
    ),
}

# Unsafe conditions and near misses per activity. With the cards above, each activity's
# events per worker-hour sit near the site rate, and lashing sits at 1.3 times it.
CONDITIONS = {
    "LASH_DECK": 7,
    "TT_DRIVING": 6,
    "REACH_STACKER": 3,
    "MOORING": 1,
    "QC_OPS": 2,
    "HOT_WORK": 1,
    "TWIST_GROUND": 1,
}
NEAR_MISSES = {
    "LASH_DECK": 3,
    "TT_DRIVING": 3,
    "REACH_STACKER": 2,
    "MOORING": 1,
    "QC_OPS": 1,
    "TWIST_GROUND": 1,
}

TEXT = {
    ACT: {
        "LASH_DECK": [
            "Climbed above the second tier without clipping on.",
            "Threw a lashing bar down to the deck instead of passing it.",
            "Stepped into the bay before the crane driver acknowledged.",
            "Worked under the spreader path while it was moving.",
        ],
        "default": [
            "Skipped the pre-start walk-around.",
            "Entered the work area without the agreed signal.",
            "Used a phone while operating.",
            "Exceeded the yard speed limit.",
        ],
    },
    BEH: {
        "LASH_DECK": [
            "Rushing to finish the bay before the break.",
            "Harness worn loose and not adjusted when asked.",
            "Ignored the buddy's call to wait for the platform.",
        ],
        "default": [
            "Rushing at the end of the shift.",
            "Did not respond to the banksman's signal straight away.",
            "Left PPE off during a short task.",
        ],
    },
    COND: {
        "LASH_DECK": [
            "Lashing platform light out on bay 14.",
            "Oil on the deck walkway near the hatch cover.",
            "Damaged lashing bar left in the working bay.",
        ],
        "default": [
            "Faded crossing markings at the aisle end.",
            "Pothole in the stacking lane.",
            "Water point empty at the start of the shift.",
        ],
    },
    SAFE: {
        "default": [
            "Clipped on before climbing and kept three points of contact.",
            "Stopped the job to clear a pedestrian from the lane.",
            "Checked the gear and reported a worn sling.",
            "Took the scheduled cool-down break and drank water.",
            "Held the toolbox talk before starting.",
        ]
    },
}


def _cohort_key(cohort: str) -> str:
    if cohort in ("new_contractor", "recent_arrival", "story"):
        return "new_contractor"
    if cohort in GROUP_PLAN:
        return cohort
    return "ungrouped"


def _random_time(ctx: Ctx, earliest: datetime, latest: datetime, night: bool | None) -> datetime:
    span = max(int((latest - earliest).total_seconds() // 86400), 1)
    day = earliest + timedelta(days=int(ctx.rng.integers(0, span)))
    if night is None:
        night = bool(ctx.rng.random() < 0.45)
    hour = int(ctx.rng.integers(16, 26)) if night else int(ctx.rng.integers(4, 14))
    return datetime(day.year, day.month, day.day) + timedelta(hours=hour)


def _text(kind: ObservationKind, activity: str, ctx: Ctx) -> str:
    options = TEXT[kind].get(activity) or TEXT[kind]["default"]
    return ctx.pick(options)


def generate_records(ctx: Ctx) -> None:
    _observation_cards(ctx)
    _conditions_and_near_misses(ctx)
    _incidents_and_hazard_reports(ctx)


def _observation_cards(ctx: Ctx) -> None:
    by_cohort: dict[str, list[int]] = {}
    for index, w in enumerate(ctx.workers):
        activity = ctx.crew_by_name[w.crew].activity
        if ctx.activity_grade[activity] < 3:
            continue
        by_cohort.setdefault(_cohort_key(w.cohort), []).append(index)

    for cohort, (cards, plan) in GROUP_PLAN.items():
        people = by_cohort.get(cohort, [])
        unsafe_slots: list[tuple[ObservationKind, str]] = []
        for activity, (acts, behaviours) in plan.items():
            unsafe_slots += [(ACT, activity)] * acts + [(BEH, activity)] * behaviours
        for n in range(cards):
            if n < len(unsafe_slots):
                kind, activity = unsafe_slots[n]
                candidates = [
                    i for i in people if ctx.crew_by_name[ctx.workers[i].crew].activity == activity
                ]
            else:
                kind, activity, candidates = SAFE, "", people
            index = candidates[n % len(candidates)] if kind != SAFE else ctx.pick(candidates)
            worker = ctx.workers[index]
            crew = ctx.crew_by_name[worker.crew]
            activity = activity or crew.activity
            earliest = max(HISTORY_START, datetime.combine(worker.hire_date, datetime.min.time()))
            night = True if (kind != SAFE and activity == "LASH_DECK") else None
            at = _random_time(ctx, earliest, CLOCK - timedelta(hours=12), night)
            ctx.add(
                Observation,
                activity_id=ctx.activity_id[activity],
                zone_id=ctx.zone_id[crew.zone],
                person_id=ctx.person_id[index],
                at=at,
                kind=kind,
                shift_kind=ShiftKind.NIGHT if (at.hour >= 15 or at.hour < 3) else ShiftKind.DAY,
                text=_text(kind, activity, ctx),
            )

    # Cards on grade 1 and 2 work: counted nowhere in the model, but part of the record.
    low = [
        i
        for i, w in enumerate(ctx.workers)
        if ctx.activity_grade[ctx.crew_by_name[w.crew].activity] < 3
    ]
    for n in range(64):
        index = ctx.pick(low)
        crew = ctx.crew_by_name[ctx.workers[index].crew]
        kind = ACT if n < 4 else SAFE
        at = _random_time(ctx, HISTORY_START, CLOCK - timedelta(hours=12), None)
        ctx.add(
            Observation,
            activity_id=ctx.activity_id[crew.activity],
            zone_id=ctx.zone_id[crew.zone],
            person_id=ctx.person_id[index],
            at=at,
            kind=kind,
            shift_kind=ShiftKind.NIGHT if (at.hour >= 15 or at.hour < 3) else ShiftKind.DAY,
            text=_text(kind, crew.activity, ctx),
        )


def _zone_for(ctx: Ctx, activity: str) -> str:
    zones = sorted({c.zone for c in ctx.crews if c.activity == activity})
    return ctx.pick(zones)


def _conditions_and_near_misses(ctx: Ctx) -> None:
    for activity, count in CONDITIONS.items():
        for _ in range(count):
            night = True if activity == "LASH_DECK" else None
            at = _random_time(ctx, HISTORY_START, CLOCK - timedelta(hours=12), night)
            ctx.add(
                Observation,
                activity_id=ctx.activity_id[activity],
                zone_id=ctx.zone_id[_zone_for(ctx, activity)],
                person_id=None,
                at=at,
                kind=COND,
                shift_kind=ShiftKind.NIGHT if (at.hour >= 15 or at.hour < 3) else ShiftKind.DAY,
                text=_text(COND, activity, ctx),
            )
    near_miss_text = {
        "LASH_DECK": "Lasher lost footing on the platform ladder; caught by the harness.",
        "TT_DRIVING": "Tractor reversed towards a walking checker; stopped in time.",
        "REACH_STACKER": "Reach stacker swung a box across the lane as a tractor entered.",
        "MOORING": "Line parted on the bollard; crew was outside the snap-back zone.",
        "QC_OPS": "Spreader landed hard on a misaligned box.",
        "HOLD_CONFINED": "Gas meter alarm during hold cleaning; crew withdrew.",
        "HOT_WORK": "Spark landed on a rag near the welding bay.",
        "TWIST_GROUND": "Spreader landed while a handler was still inside the bay.",
        "WORKSHOP_MECH": "Jack slipped under a raised tractor; nobody underneath.",
    }
    for activity, count in NEAR_MISSES.items():
        if activity in ("LASH_DECK", "REACH_STACKER"):
            continue  # placed by the injected events (June nights, early July)
        for _ in range(count):
            at = _random_time(ctx, HISTORY_START, CLOCK - timedelta(hours=12), None)
            ctx.add(
                NearMiss,
                activity_id=ctx.activity_id[activity],
                zone_id=ctx.zone_id[_zone_for(ctx, activity)],
                reported_by=None,
                at=at,
                shift_kind=ShiftKind.NIGHT if (at.hour >= 15 or at.hour < 3) else ShiftKind.DAY,
                text=near_miss_text[activity],
                potential_severity=int(ctx.rng.integers(3, 6)),
                status=RecordStatus.CLOSED,
            )


INCIDENTS = [
    ("TT_DRIVING", IncidentKind.INJURY, "Driver strained a shoulder coupling a trailer.", 2, False),
    (
        "TT_DRIVING",
        IncidentKind.PROPERTY,
        "Tractor clipped a light pole at the aisle end.",
        1,
        False,
    ),
    (
        "TT_DRIVING",
        IncidentKind.INJURY,
        "Checker's foot run over at low speed in the lane.",
        3,
        True,
    ),
    ("REACH_STACKER", IncidentKind.PROPERTY, "Container dropped onto the stack corner.", 2, False),
    ("MOORING", IncidentKind.INJURY, "Hand caught between line and bollard.", 3, True),
    ("WORKSHOP_MECH", IncidentKind.INJURY, "Back strain lifting a gearbox by hand.", 2, True),
    ("WORKSHOP_MECH", IncidentKind.INJURY, "Cut to the forearm on a sharp bracket.", 1, False),
    ("REEFER", IncidentKind.INJURY, "Minor burn from a hot plug housing.", 1, False),
    ("HOT_WORK", IncidentKind.ENVIRONMENT, "Small oil spill from the welding generator.", 1, False),
]

HAZARD_TEXT = [
    "Broken handrail on the berth stairs.",
    "Lighting out along the reefer rack walkway.",
    "Standing water near the gate booth.",
    "Missing cover on a cable trench in the yard.",
    "Drinking water point warm at midday.",
    "Loose grating on the quay apron.",
    "Blind corner at the end of row 14 needs a mirror.",
    "Cooling unit noisy and blowing warm air in the rest cabin.",
]


def _incidents_and_hazard_reports(ctx: Ctx) -> None:
    hse = ctx.key_person["layla.haddad"]
    for activity, kind, text, severity, lost_time in INCIDENTS:
        at = _random_time(ctx, HISTORY_START, datetime(2026, 6, 20), None)
        ctx.add(
            Incident,
            activity_id=ctx.activity_id[activity],
            zone_id=ctx.zone_id[_zone_for(ctx, activity)],
            reported_by=hse,
            at=at,
            shift_kind=ShiftKind.NIGHT if (at.hour >= 15 or at.hour < 3) else ShiftKind.DAY,
            kind=kind,
            text=text,
            photo_key=None,
            potential_severity=min(severity + 2, 5),
            actual_severity=severity,
            lost_time=lost_time,
            status=RecordStatus.CLOSED,
            closed_at=at + timedelta(days=12),
        )
    zones = [c.zone for c in ctx.crews]
    for _ in range(72):
        at = _random_time(ctx, HISTORY_START, CLOCK - timedelta(hours=6), None)
        ctx.add(
            HazardReport,
            activity_id=None,
            zone_id=ctx.zone_id[ctx.pick(zones)],
            reported_by=None,
            at=at,
            text=ctx.pick(HAZARD_TEXT),
            status=RecordStatus.CLOSED if at < CLOCK - timedelta(days=10) else RecordStatus.OPEN,
        )
