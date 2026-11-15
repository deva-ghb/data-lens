"""Signals from outside the safety system: weather, sensors, air, clinic, camp and labs.

`generate_signals` writes the source records (clinic visits, camp tickets, lab panels,
hourly weather and sensor readings). `ingest_feeds` then turns the records into the
per-zone series each feed delivers, which is what the early warning detector reads.
"""

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.feeds.wbgt import estimate_wbgt
from app.models import (
    Absence,
    Assignment,
    CampTicket,
    CheckIn,
    ClinicVisit,
    Feed,
    FeedReading,
    FitnessOutcome,
    HazardReport,
    LabPanel,
    NearMiss,
    Observation,
    Shift,
    TrainingRecord,
    UnwellEvent,
)
from app.models.feeds import FeedSource, SignalClass
from app.models.health import FitnessDecision
from app.models.records import ObservationKind
from seed.context import Ctx
from seed.scenario import CLOCK, HISTORY_START, roster_days

ARCHIVE = Path(__file__).resolve().parent / "data" / "abu_dhabi_2025_hourly.json"

FEEDS = [
    ("CLINIC_VISITS", "Clinic visits by syndrome", SignalClass.CLINICAL, 1440, 1440, "camp block"),
    ("LAB_PANELS", "Lab panels (clinician reviewed)", SignalClass.CLINICAL, 1440, 4320, "cohort"),
    ("SICKNESS_ABSENCE", "Sickness absence", SignalClass.WORKPLACE, 720, 720, "work zone"),
    ("ROSTER", "Roster and shift pattern", SignalClass.WORKPLACE, 720, 720, "work zone"),
    (
        "SAFETY_REPORTS",
        "Incident, near-miss, hazard and observation reports",
        SignalClass.WORKPLACE,
        60,
        240,
        "work zone",
    ),
    ("TRAINING", "Training and competency records", SignalClass.WORKPLACE, 1440, 2880, "person"),
    (
        "WEATHER",
        "Weather forecast and on-site WBGT",
        SignalClass.ENVIRONMENTAL,
        60,
        120,
        "terminal",
    ),
    ("AIR_QUALITY", "Air quality (PM10, PM2.5)", SignalClass.ENVIRONMENTAL, 60, 120, "district"),
    (
        "CAMP_TICKETS",
        "Accommodation fault tickets",
        SignalClass.COMMUNITY,
        1440,
        1440,
        "camp block",
    ),
    ("CHECKINS", "Three-tap check-ins", SignalClass.WORKER_REPORTED, 720, 60, "work zone"),
]

SYNDROMES = ["heat", "respiratory", "musculoskeletal", "injury", "gastro", "other"]
CAMP_BLOCKS = ["Camp Block A", "Camp Block B", "Camp Block C", "Camp Block D", "Camp Block E"]
VILLAGE = "Mirsal Village District"
PORT = "Mirsal Port District"


def create_feeds(ctx: Ctx) -> None:
    for code, name, signal_class, cadence, delay, level in FEEDS:
        feed = Feed(
            code=code,
            name=name,
            signal_class=signal_class,
            cadence_minutes=cadence,
            allowed_delay_minutes=delay,
            location_level=level,
            enabled=True,
            source=FeedSource.SEEDED,
        )
        ctx.session.add(feed)
        ctx.session.flush()
        ctx.feed_id[code] = feed.id


def generate_signals(ctx: Ctx) -> None:
    weather = _weather(ctx)
    _air_quality(ctx)
    _clinic_visits(ctx, weather)
    _camp_tickets(ctx)
    _labs_and_outcomes(ctx)


def load_archive() -> dict[datetime, dict[str, float]]:
    """Real 2025 hourly weather keyed by the same hour in 2026."""
    raw = json.loads(ARCHIVE.read_text())
    out: dict[datetime, dict[str, float]] = {}
    for i, stamp in enumerate(raw["time"]):
        t = datetime.fromisoformat(stamp).replace(year=2026)
        out[t] = {
            "temp_c": raw["temp_c"][i],
            "rh_pct": raw["rh_pct"][i],
            "wind_ms": raw["wind_ms"][i],
            "radiation_wm2": raw["radiation_wm2"][i],
        }
    return out


def _weather(ctx: Ctx) -> dict[date, float]:
    """Hourly forecast readings (through 30 July) and deck sensors (up to the clock).

    Returns the day's peak estimated WBGT, used to shape heat visits at the clinic.
    """
    archive = load_archive()
    feed = ctx.feed_id["WEATHER"]
    peak: dict[date, float] = defaultdict(float)
    berth_offset = {1: 0.4, 2: 0.7, 3: 0.5, 4: 0.3}
    for t, values in sorted(archive.items()):
        if t < datetime(2026, 5, 1) or t > datetime(2026, 7, 30, 23):
            continue
        for metric, value in values.items():
            ctx.add(
                FeedReading,
                feed_id=feed,
                zone_id=None,
                at=t,
                metric=metric,
                value=value,
                source=FeedSource.SEEDED,
            )
        wbgt = estimate_wbgt(values["temp_c"], values["rh_pct"], values["radiation_wm2"])
        local_day = (t + timedelta(hours=4)).date()
        peak[local_day] = max(peak[local_day], wbgt)
        if t <= CLOCK:
            for berth, offset in berth_offset.items():
                reading = round(wbgt + offset + float(ctx.rng.normal(0, 0.35)), 2)
                ctx.add(
                    FeedReading,
                    feed_id=feed,
                    zone_id=ctx.zone_id[f"Berth {berth}"],
                    at=t,
                    metric="deck_wbgt",
                    value=reading,
                    source=FeedSource.SEEDED,
                )
    return peak


def _air_quality(ctx: Ctx) -> None:
    feed = ctx.feed_id["AIR_QUALITY"]
    zone = ctx.zone_id[PORT]
    t = datetime(2026, 5, 1)
    while t <= CLOCK:
        pm10 = float(ctx.rng.lognormal(mean=4.45, sigma=0.25))  # about 85 ug/m3 median
        ctx.add(
            FeedReading,
            feed_id=feed,
            zone_id=zone,
            at=t,
            metric="pm10",
            value=round(pm10, 1),
            source=FeedSource.SEEDED,
        )
        ctx.add(
            FeedReading,
            feed_id=feed,
            zone_id=zone,
            at=t,
            metric="pm25",
            value=round(pm10 * 0.38, 1),
            source=FeedSource.SEEDED,
        )
        t += timedelta(hours=1)


def residents(ctx: Ctx) -> dict[str, list[int]]:
    by_block: dict[str, list[int]] = defaultdict(list)
    for index, w in enumerate(ctx.workers):
        by_block[w.camp or VILLAGE].append(ctx.person_id[index])
    return by_block


def add_visit(
    ctx: Ctx, person_id: int, home: str, at: datetime, syndrome: str, located: bool | None = None
) -> None:
    if located is None:
        located = bool(ctx.rng.random() < 0.62)
    zone = home if (located and home in CAMP_BLOCKS) else VILLAGE
    ctx.add(
        ClinicVisit,
        clinic_id=ctx.clinic_id,
        person_id=person_id,
        zone_id=ctx.zone_id[zone],
        at=at,
        syndrome=syndrome,
    )


def _clinic_visits(ctx: Ctx, peak_wbgt: dict[date, float]) -> None:
    """Daily visits per resident. Heat visits follow the day's peak WBGT.

    Camp Block C's located heat visits from 27 June are fixed at two a day, so the injected
    cooling failure (two extra a day from 25 July) reads as double the usual.
    """
    rates = {
        "respiratory": 0.0035,
        "musculoskeletal": 0.004,
        "injury": 0.0015,
        "gastro": 0.0025,
        "other": 0.004,
    }
    homes = residents(ctx)
    for day in roster_days():
        noon = datetime(day.year, day.month, day.day, 6)
        if noon > CLOCK:
            break
        heat_rate = 0.0012 + 0.0009 * max(peak_wbgt.get(day, 30) - 30, 0)
        for home, people in homes.items():
            for syndrome, rate in [("heat", heat_rate), *rates.items()]:
                if home == "Camp Block C" and syndrome == "heat" and day >= date(2026, 6, 27):
                    count = 0  # set exactly below
                else:
                    count = int(ctx.rng.poisson(rate * len(people)))
                for _ in range(count):
                    at = noon + timedelta(minutes=int(ctx.rng.integers(0, 600)))
                    add_visit(ctx, ctx.pick(people), home, at, syndrome)
            if home == "Camp Block C" and day >= date(2026, 6, 27):
                for _ in range(2):
                    at = noon + timedelta(minutes=int(ctx.rng.integers(0, 600)))
                    add_visit(ctx, ctx.pick(people), home, at, "heat", located=True)


def _camp_tickets(ctx: Ctx) -> None:
    kinds = ["plumbing", "electrical", "cooling_failure", "pest", "laundry"]
    for block in CAMP_BLOCKS:
        zone = ctx.zone_id[block]
        for day in roster_days():
            opened = datetime(day.year, day.month, day.day, int(ctx.rng.integers(2, 18)))
            if opened > CLOCK - timedelta(hours=2):
                break
            for _ in range(int(ctx.rng.poisson(0.35))):
                kind = ctx.pick(kinds)
                units = int(ctx.rng.integers(1, 3)) if kind == "cooling_failure" else 1
                ctx.add(
                    CampTicket,
                    zone_id=zone,
                    opened_at=opened,
                    closed_at=opened + timedelta(hours=int(ctx.rng.integers(6, 40))),
                    kind=kind,
                    units_affected=units,
                    units_total=40,
                )


def _labs_and_outcomes(ctx: Ctx) -> None:
    clinician = ctx.key_person["sara.ibrahim"]
    enrolled = [ctx.person_id[i] for i in range(len(ctx.workers)) if ctx.rng.random() < 0.5]
    panels = [("creatinine", 0.9, 0.18, 1.3), ("hba1c", 5.5, 0.5, 6.5), ("sodium", 140, 2.5, 146)]
    for pid in enrolled:
        first = datetime(2026, 5, 1) + timedelta(days=int(ctx.rng.integers(0, 85)), hours=5)
        for panel, mean, sd, high in panels:
            value = round(float(ctx.rng.normal(mean, sd)), 2)
            ctx.add(
                LabPanel,
                person_id=pid,
                at=first,
                panel=panel,
                value=value,
                flag="high" if value >= high else None,
            )
    sample = [ctx.person_id[int(i)] for i in ctx.rng.choice(len(ctx.workers), 14, replace=False)]
    for pid in sample:
        at = datetime(2026, 5, 3) + timedelta(days=int(ctx.rng.integers(0, 80)), hours=6)
        decision = (
            FitnessDecision.FIT if ctx.rng.random() < 0.7 else FitnessDecision.FIT_WITH_RESTRICTIONS
        )
        ctx.add(
            FitnessOutcome,
            person_id=pid,
            decided_by=clinician,
            at=at,
            outcome=decision,
            restriction_text=None
            if decision == FitnessDecision.FIT
            else "No work above the second tier for 7 days.",
            share_with_employer=bool(ctx.rng.random() < 0.85),
        )
    # One of Marco's gang mates, cleared by the clinician on 19 July.
    gang3 = [
        ctx.person_id[i]
        for i, w in enumerate(ctx.workers)
        if w.crew == "Deck Gang 3" and w.cohort == "exp_inhouse"
    ]
    ctx.add(
        FitnessOutcome,
        person_id=gang3[0],
        decided_by=clinician,
        at=datetime(2026, 7, 19, 6, 30),
        outcome=FitnessDecision.FIT,
        restriction_text=None,
        share_with_employer=True,
    )
    for pid in sample[:3]:
        day = ctx.worked[pid][len(ctx.worked[pid]) // 2] if ctx.worked[pid] else None
        if day is None:
            continue
        ctx.add(
            UnwellEvent,
            person_id=pid,
            shift_id=ctx.shift_id[(day[0], day[1])],
            at=datetime(day[0].year, day[0].month, day[0].day, 9),
            permit_id=None,
        )


# ----------------------------------------------------------------------------------------
# Ingestion: each feed's per-zone series.


def _day_start(at: datetime) -> datetime:
    local = at + timedelta(hours=4)
    return datetime(local.year, local.month, local.day) - timedelta(hours=4)


def ingest_feeds(ctx: Ctx) -> None:
    s = ctx.session
    rows: list[dict] = []
    days = [
        d for d in roster_days() if datetime(d.year, d.month, d.day) - timedelta(hours=4) <= CLOCK
    ]

    def series(feed: str, zone: str | None, at: datetime, metric: str, value: float) -> None:
        rows.append(
            {
                "feed_id": ctx.feed_id[feed],
                "zone_id": ctx.zone_id[zone] if zone else None,
                "at": at,
                "metric": metric,
                "value": float(value),
                "source": FeedSource.SEEDED,
            }
        )

    # Clinic visits: daily counts per camp block (and the district for unlocated visits).
    zone_name = {v: k for k, v in ctx.zone_id.items()}
    counts: Counter = Counter()
    for zone_id, at, syndrome in s.execute(
        select(ClinicVisit.zone_id, ClinicVisit.at, ClinicVisit.syndrome)
    ):
        counts[(zone_name[zone_id], _day_start(at), syndrome)] += 1
    for d in days:
        start = datetime(d.year, d.month, d.day) - timedelta(hours=4)
        for zone in [*CAMP_BLOCKS, VILLAGE]:
            for syndrome in SYNDROMES:
                series(
                    "CLINIC_VISITS",
                    zone,
                    start,
                    f"{syndrome}_visits",
                    counts[(zone, start, syndrome)],
                )

    # Lab panels: daily tested and flagged, cohort level (no zone).
    labs: Counter = Counter()
    for at, flag in s.execute(select(LabPanel.at, LabPanel.flag)):
        labs[(_day_start(at), "tested")] += 1
        if flag:
            labs[(_day_start(at), "flagged")] += 1
    for d in days:
        start = datetime(d.year, d.month, d.day) - timedelta(hours=4)
        series("LAB_PANELS", None, start, "panels_tested", labs[(start, "tested")])
        series("LAB_PANELS", None, start, "panels_flagged", labs[(start, "flagged")])

    # Roster, absence and check-ins: per shift (or day) per work zone.
    shift_rows = {
        sid: (d, k, st)
        for sid, d, k, st in s.execute(select(Shift.id, Shift.date, Shift.kind, Shift.start_at))
    }
    rostered: Counter = Counter()
    person_zone_on: dict[tuple[int, date], str] = {}
    for sid, pid, zone_id in s.execute(
        select(Assignment.shift_id, Assignment.person_id, Assignment.zone_id)
    ):
        d, _, start = shift_rows[sid]
        rostered[(zone_name[zone_id], start)] += 1
        person_zone_on[(pid, d)] = zone_name[zone_id]
    home_zone = {ctx.person_id[i]: ctx.crew_by_name[w.crew].zone for i, w in enumerate(ctx.workers)}
    work_zones = sorted({c.zone for c in ctx.crews})
    for _sid, (_d, _, start) in sorted(shift_rows.items(), key=lambda item: item[1][2]):
        if start > CLOCK + timedelta(hours=40):
            continue
        for zone in work_zones:
            series("ROSTER", zone, start, "rostered", rostered[(zone, start)])
    absent: Counter = Counter()
    for pid, d in s.execute(select(Absence.person_id, Absence.date)):
        absent[(home_zone.get(pid, PORT), d)] += 1
    for d in days:
        start = datetime(d.year, d.month, d.day) - timedelta(hours=4)
        for zone in work_zones:
            series("SICKNESS_ABSENCE", zone, start, "absent", absent[(zone, d)])
    checks: Counter = Counter()
    for sid, pid, band, feeling in s.execute(
        select(CheckIn.shift_id, CheckIn.person_id, CheckIn.sleep_hours_band, CheckIn.feeling)
    ):
        d, _, start = shift_rows[sid]
        zone = person_zone_on.get((pid, d), home_zone.get(pid, PORT))
        checks[(zone, start, "checkins")] += 1
        if feeling == "tired":
            checks[(zone, start, "tired")] += 1
        if feeling == "unwell":
            checks[(zone, start, "unwell")] += 1
        if band in ("under_5", "5_to_6"):
            checks[(zone, start, "short_sleep")] += 1
    for _sid, (_d, _, start) in sorted(shift_rows.items(), key=lambda item: item[1][2]):
        if start > CLOCK:
            continue
        for zone in work_zones:
            for metric in ("checkins", "tired", "unwell", "short_sleep"):
                series("CHECKINS", zone, start, metric, checks[(zone, start, metric)])

    # Safety reports: daily per work zone, over the full twelve months.
    reports: Counter = Counter()
    for zone_id, at, kind in s.execute(
        select(Observation.zone_id, Observation.at, Observation.kind)
    ):
        if kind != ObservationKind.SAFE:
            reports[(zone_name[zone_id], _day_start(at))] += 1
    for zone_id, at in s.execute(select(NearMiss.zone_id, NearMiss.at)):
        reports[(zone_name[zone_id], _day_start(at))] += 1
    for zone_id, at in s.execute(select(HazardReport.zone_id, HazardReport.at)):
        reports[(zone_name[zone_id], _day_start(at))] += 1
    day = _day_start(HISTORY_START)
    while day <= CLOCK:
        for zone in work_zones:
            series("SAFETY_REPORTS", zone, day, "unsafe_reports", reports[(zone, day)])
        day += timedelta(days=1)

    # Training: completions per day.
    training: Counter = Counter()
    for (done,) in s.execute(select(TrainingRecord.completed_on)):
        training[done] += 1
    for d in days:
        series(
            "TRAINING",
            None,
            datetime(d.year, d.month, d.day) - timedelta(hours=4),
            "completions",
            training[d],
        )

    # Camp tickets: opened per day and cooling units down at the end of each day.
    tickets = list(
        s.execute(
            select(
                CampTicket.zone_id,
                CampTicket.opened_at,
                CampTicket.closed_at,
                CampTicket.kind,
                CampTicket.units_affected,
            )
        )
    )
    for d in days:
        start = datetime(d.year, d.month, d.day) - timedelta(hours=4)
        end = min(start + timedelta(days=1), CLOCK)
        for block in CAMP_BLOCKS:
            zone_id = ctx.zone_id[block]
            opened = sum(1 for z, o, _, _, _ in tickets if z == zone_id and start <= o < end)
            down = sum(
                u
                for z, o, c, k, u in tickets
                if z == zone_id and k == "cooling_failure" and o < end and (c is None or c > end)
            )
            series("CAMP_TICKETS", block, start, "tickets_opened", opened)
            series("CAMP_TICKETS", block, start, "cooling_units_down", down)

    for start in range(0, len(rows), 5000):
        s.execute(FeedReading.__table__.insert(), rows[start : start + 5000])
    s.flush()
