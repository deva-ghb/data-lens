"""Injected events: the ground truth the back-test measures against.

Four real events, each written into at least two different signal classes, each with
the moment harm would have followed (`harm_at`) so lead time can be measured. Two
decoys look like a pattern for a day or two and are followed by nothing: they are
how the back-test sees false alarms.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.models import (
    Absence,
    CampTicket,
    CheckIn,
    FeedReading,
    HazardReport,
    Incident,
    NearMiss,
)
from app.models.records import IncidentKind, RecordStatus
from app.models.roster import Feeling, ShiftKind
from seed.context import Ctx
from seed.signals import add_visit, residents


@dataclass(frozen=True)
class InjectedEvent:
    code: str
    zone: str
    signal_start: datetime
    harm_at: datetime
    signals: tuple[str, ...]
    closed: bool
    summary: str


INJECTED_EVENTS = [
    InjectedEvent(
        "E1_DUST_RESP",
        "Yard Block 4",
        datetime(2026, 5, 12),
        datetime(2026, 5, 18, 6),
        ("AIR_QUALITY", "CLINIC_VISITS", "SICKNESS_ABSENCE"),
        True,
        "Dust event: PM10 high for four days, respiratory visits and absence among Yard Block 4 crews.",
    ),
    InjectedEvent(
        "E2_NIGHT_FATIGUE",
        "Berth 3",
        datetime(2026, 6, 8),
        datetime(2026, 6, 16, 2),
        ("SAFETY_REPORTS", "CHECKINS"),
        True,
        "Night lashing fatigue: three near misses and a run of tired check-ins at Berth 3.",
    ),
    InjectedEvent(
        "E3_PLANT_STRUCK",
        "Yard Block 2",
        datetime(2026, 7, 1),
        datetime(2026, 7, 8, 7),
        ("SAFETY_REPORTS", "CHECKINS"),
        True,
        "Reach stacker and tractor conflicts in Yard Block 2 after an overtime week.",
    ),
    InjectedEvent(
        "E4_CAMP_C_COOLING",
        "Camp Block C",
        datetime(2026, 7, 24),
        datetime(2026, 7, 30, 22),
        ("CAMP_TICKETS", "CLINIC_VISITS"),
        False,
        "Camp Block C: 11 of 40 cooling units down, heat visits at the clinic about double.",
    ),
]

DECOYS = [
    ("D1_CAMP_B_GASTRO", "Camp Block B", date(2026, 6, 14)),
    ("D2_YARD_6_DUST", "Yard Block 6", date(2026, 6, 2)),
]


def inject(ctx: Ctx) -> None:
    _e1_dust(ctx)
    _e2_night_fatigue(ctx)
    _e3_plant(ctx)
    _e4_camp_c(ctx)
    _decoys(ctx)


def _bump_pm10(ctx: Ctx, start: datetime, hours: int, factor: float) -> None:
    feed = ctx.feed_id["AIR_QUALITY"]
    end = start + timedelta(hours=hours)
    for row in ctx.rows[FeedReading]:
        if row["feed_id"] == feed and start <= row["at"] < end:
            row["value"] = round(row["value"] * factor, 1)


def _sick(ctx: Ctx, people: list[tuple[int, str]], day: date, count: int) -> None:
    """Mark rostered workers off sick on a day: an absence, and no check-in that day."""
    rostered = [pid for pid, _ in people if any(d == day for d, _, _, _ in ctx.worked.get(pid, []))]
    for _ in range(count):
        if not rostered:
            return
        pid = ctx.pick(rostered)
        rostered.remove(pid)
        ctx.add(Absence, person_id=pid, date=day, kind="sickness")
        shift_ids = {sid for (d, _k), sid in ctx.shift_id.items() if d == day}
        ctx.rows[CheckIn] = [
            r
            for r in ctx.rows[CheckIn]
            if not (r["person_id"] == pid and r["shift_id"] in shift_ids)
        ]


def _crew_people(ctx: Ctx, crews: set[str]) -> list[tuple[int, str]]:
    return [
        (ctx.person_id[i], w.camp or "Mirsal Village District")
        for i, w in enumerate(ctx.workers)
        if w.crew in crews
    ]


def _e1_dust(ctx: Ctx) -> None:
    _bump_pm10(ctx, datetime(2026, 5, 11, 20), 96, 3.4)
    people = _crew_people(ctx, {"Yard Gang 4", "Yard Gang 10"})
    for offset in range(5):
        day = datetime(2026, 5, 12) + timedelta(days=offset)
        for _ in range(3):
            pid, home = ctx.pick(people)
            add_visit(
                ctx,
                pid,
                home,
                day + timedelta(hours=6 + int(ctx.rng.integers(0, 8))),
                "respiratory",
            )
        _sick(ctx, people, day.date(), 2)


def _e2_night_fatigue(ctx: Ctx) -> None:
    lash = ctx.activity_id["LASH_DECK"]
    for when in (datetime(2026, 6, 8, 22), datetime(2026, 6, 9, 23), datetime(2026, 6, 11, 22)):
        ctx.add(
            NearMiss,
            activity_id=lash,
            zone_id=ctx.zone_id["Berth 3"],
            reported_by=None,
            at=when,
            shift_kind=ShiftKind.NIGHT,
            text="Lasher lost footing on the platform ladder on a fourth night; caught by the harness.",
            potential_severity=5,
            status=RecordStatus.CLOSED,
        )
    ctx.add(
        HazardReport,
        activity_id=lash,
        zone_id=ctx.zone_id["Berth 3"],
        reported_by=None,
        at=datetime(2026, 6, 10, 21),
        text="Rung loose on the lashing platform ladder at bay 22; crew are rushing past it.",
        status=RecordStatus.CLOSED,
    )
    _tired_run(
        ctx,
        {"Deck Gang 4", "Deck Gang 7"},
        date(2026, 6, 8),
        date(2026, 6, 13),
        ShiftKind.NIGHT,
        0.45,
    )


def _e3_plant(ctx: Ctx) -> None:
    rs = ctx.activity_id["REACH_STACKER"]
    for when in (datetime(2026, 7, 2, 9), datetime(2026, 7, 4, 7)):
        ctx.add(
            NearMiss,
            activity_id=rs,
            zone_id=ctx.zone_id["Yard Block 2"],
            reported_by=None,
            at=when,
            shift_kind=ShiftKind.DAY,
            text="Reach stacker swung a box across the lane as a tractor entered.",
            potential_severity=5,
            status=RecordStatus.CLOSED,
        )
    ctx.add(
        HazardReport,
        activity_id=rs,
        zone_id=ctx.zone_id["Yard Block 2"],
        reported_by=None,
        at=datetime(2026, 7, 3, 11),
        text="Convex mirror at the row 9 crossing is broken; tractors are entering blind.",
        status=RecordStatus.CLOSED,
    )
    _tired_run(ctx, {"Yard Gang 2", "Yard Gang 8"}, date(2026, 7, 1), date(2026, 7, 5), None, 0.4)
    ctx.add(
        Incident,
        activity_id=ctx.activity_id["TT_DRIVING"],
        zone_id=ctx.zone_id["Yard Block 2"],
        reported_by=ctx.key_person["layla.haddad"],
        at=datetime(2026, 7, 8, 7),
        shift_kind=ShiftKind.DAY,
        kind=IncidentKind.INJURY,
        text="Tractor driver struck at low speed by a reach stacker counterweight while walking to his cab.",
        photo_key=None,
        potential_severity=5,
        actual_severity=3,
        lost_time=True,
        status=RecordStatus.CLOSED,
        closed_at=datetime(2026, 7, 20, 10),
    )


def _tired_run(
    ctx: Ctx, crews: set[str], first: date, last: date, kind: ShiftKind | None, share: float
) -> None:
    people = {pid for pid, _ in _crew_people(ctx, crews)}
    shift_ids = {
        sid
        for (d, k), sid in ctx.shift_id.items()
        if first <= d <= last and (kind is None or k == kind.value)
    }
    for row in ctx.rows[CheckIn]:
        if row["person_id"] in people and row["shift_id"] in shift_ids and ctx.rng.random() < share:
            row["feeling"] = Feeling.TIRED
            row["sleep_hours_band"] = "under_5" if ctx.rng.random() < 0.5 else "5_to_6"


def _e4_camp_c(ctx: Ctx) -> None:
    zone = ctx.zone_id["Camp Block C"]
    for when, units in ((datetime(2026, 7, 24, 2), 6), (datetime(2026, 7, 25, 1), 5)):
        ctx.add(
            CampTicket,
            zone_id=zone,
            opened_at=when,
            closed_at=None,
            kind="cooling_failure",
            units_affected=units,
            units_total=40,
        )
    # Remove any routine cooling ticket left open in Camp C over the same days.
    ctx.rows[CampTicket] = [
        r
        for r in ctx.rows[CampTicket]
        if not (
            r["zone_id"] == zone
            and r["kind"] == "cooling_failure"
            and r["opened_at"] >= datetime(2026, 7, 20)
            and r["closed_at"] is not None
        )
        or r["closed_at"] is None
    ]
    homes = residents(ctx)["Camp Block C"]
    for offset in range(8):
        day = datetime(2026, 7, 25, 6) + timedelta(days=offset // 2)
        add_visit(
            ctx,
            ctx.pick(homes),
            "Camp Block C",
            day + timedelta(minutes=int(ctx.rng.integers(0, 600))),
            "heat",
            located=True,
        )


def _decoys(ctx: Ctx) -> None:
    # D1: a one-off stomach bug in Camp B with a plumbing fault the same day. Nothing follows.
    homes = residents(ctx)["Camp Block B"]
    day = datetime(2026, 6, 14, 6)
    for _ in range(4):
        add_visit(
            ctx,
            ctx.pick(homes),
            "Camp Block B",
            day + timedelta(minutes=int(ctx.rng.integers(0, 500))),
            "gastro",
            located=True,
        )
    for hours in (1, 3, 5):
        ctx.add(
            CampTicket,
            zone_id=ctx.zone_id["Camp Block B"],
            opened_at=datetime(2026, 6, 14, hours),
            closed_at=datetime(2026, 6, 14, hours + 9),
            kind="plumbing",
            units_affected=1,
            units_total=40,
        )
    # D2: a dusty afternoon and two absences in Yard Block 6. Nothing follows.
    _bump_pm10(ctx, datetime(2026, 6, 2, 8), 10, 2.6)
    people = _crew_people(ctx, {"Housekeeping Crew", "Reefer Team 2"})
    _sick(ctx, people, date(2026, 6, 2), 3)
