"""Build the synthetic Mirsal Terminals history: raw records only.

Order: reference data, people, roster and check-ins, safety records, signals, then the
injected events adjust the pending rows, then everything is written and the feeds are
ingested as the per-zone series the detector reads. Nothing derived (scores, tiers,
warnings, group rates) is written here.
"""

from datetime import date, datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.engine.weights import ensure_weights_v0
from app.models import (
    Absence,
    Activity,
    ActivityHazard,
    Assignment,
    CheckIn,
    Clinic,
    Competency,
    Employer,
    Gang,
    Hazard,
    Permit,
    PermitEvent,
    Person,
    PersonCompetency,
    Setting,
    Shift,
    SiteClock,
    SwpItem,
    TrainingRecord,
    VesselCall,
    Zone,
)
from app.models.permits import PermitStatus
from app.models.roster import AssignmentSource, Feeling, ShiftKind
from seed import catalog, events, records, signals
from seed.context import Ctx
from seed.scenario import CLOCK, ROSTER_START, STORY_DATE, roster_days, shift_window
from seed.workforce import build_crews, build_workers, foreman_names


def generate(session: Session, rng: np.random.Generator) -> None:
    ctx = Ctx(session=session, rng=rng)
    _reference(ctx)
    _people(ctx)
    _roster(ctx)
    _vessels_and_permits(ctx)
    records.generate_records(ctx)
    signals.generate_signals(ctx)
    events.inject(ctx)
    session.add(
        Setting(
            key="injected_events",
            value=[
                {
                    "code": e.code,
                    "zone": e.zone,
                    "signal_start": e.signal_start.isoformat(),
                    "harm_at": e.harm_at.isoformat(),
                    "signals": list(e.signals),
                    "closed": e.closed,
                    "summary": e.summary,
                }
                for e in events.INJECTED_EVENTS
            ],
        )
    )
    _fix_story_checkins(ctx)
    ctx.flush_rows(*list(ctx.rows))
    signals.ingest_feeds(ctx)
    session.flush()


def _reference(ctx: Ctx) -> None:
    s = ctx.session
    for e in catalog.EMPLOYERS:
        row = Employer(name=e.name, kind=e.kind, logo_key=e.logo_key)
        s.add(row)
        s.flush()
        ctx.employer_id[e.name] = row.id
    for z in catalog.ZONES:
        zone = Zone(name=z.name, kind=z.kind, parent_id=ctx.zone_id.get(z.parent or ""))
        s.add(zone)
        s.flush()
        ctx.zone_id[z.name] = zone.id
    clinic = Clinic(name=catalog.CLINIC_NAME, zone_id=ctx.zone_id[catalog.CLINIC_ZONE])
    s.add(clinic)
    for c in catalog.COMPETENCIES:
        comp = Competency(code=c.code, name=c.name)
        s.add(comp)
        s.flush()
        ctx.competency_id[c.code] = comp.id
    hazard_id = {}
    for h in catalog.HAZARDS:
        hz = Hazard(code=h.code, name=h.name)
        s.add(hz)
        s.flush()
        hazard_id[h.code] = hz.id
    for a in catalog.ACTIVITIES:
        act = Activity(
            code=a.code,
            name=a.name,
            grade=a.grade,
            exposure_hours_week=a.exposure_hours_week,
            severity=a.severity,
            competency_id=ctx.competency_id[a.competency],
        )
        s.add(act)
        s.flush()
        ctx.activity_id[a.code] = act.id
        ctx.activity_grade[a.code] = a.grade
        for code in a.hazards:
            s.add(ActivityHazard(activity_id=act.id, hazard_id=hazard_id[code]))
        for seq, text in enumerate(a.swp_items, start=1):
            s.add(SwpItem(activity_id=act.id, seq=seq, text=text))
    for a in catalog.ACTIVITIES:
        if a.lower_hazard_alternative:
            s.get_one(
                Activity, ctx.activity_id[a.code]
            ).lower_hazard_alternative_id = ctx.activity_id[a.lower_hazard_alternative]
    s.flush()
    ctx.clinic_id = clinic.id
    signals.create_feeds(ctx)
    ensure_weights_v0(s)
    s.add(SiteClock(id=1, now=CLOCK))
    s.add(Setting(key="small_cell_threshold", value=10))
    s.add(Setting(key="scenario", value={"story_date": STORY_DATE.isoformat()}))
    s.flush()


def _person_row(ctx: Ctx, **values: object) -> int:
    person = Person(**values)
    ctx.session.add(person)
    ctx.session.flush()
    return person.id


def _people(ctx: Ctx) -> None:
    password_hash = hash_password(catalog.PASSWORD)
    ctx.crews = build_crews(ctx.rng)
    ctx.crew_by_name = {c.name: c for c in ctx.crews}
    ctx.workers = build_workers(ctx.rng, ctx.crews)
    today = STORY_DATE

    for user in catalog.KEY_USERS:
        if user.role == "worker":
            continue
        pid = _person_row(
            ctx,
            employer_id=ctx.employer_id[user.employer],
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role=user.role,
            job_title=user.job_title,
            hire_date=today - timedelta(days=1800),
            site_arrival_date=today - timedelta(days=1800),
            induction=user.induction,
            camp_zone_id=None,
            display_language=user.display_language,
            password_hash=password_hash,
        )
        ctx.key_person[user.email.split("@")[0]] = pid

    taken = {w.email_local for w in ctx.workers} | set(ctx.key_person)
    foremen = foreman_names(ctx.rng, ctx.crews, taken)
    for crew in ctx.crews:
        if crew.name == "Deck Gang 3":
            foreman_id = ctx.key_person["joseph.kariuki"]
        elif crew.name == "Yard Gang 1":
            foreman_id = ctx.key_person["tomas.reyes"]
        else:
            first, last = foremen[crew.name]
            foreman_id = _person_row(
                ctx,
                employer_id=ctx.employer_id["Mirsal Terminals"],
                first_name=first,
                last_name=last,
                email=f"{first}.{last}@{catalog.EMAIL_DOMAIN}".lower(),
                role="foreman",
                job_title=f"Foreman, {crew.name}",
                hire_date=today - timedelta(days=2400),
                site_arrival_date=today - timedelta(days=2400),
                induction="site",
                camp_zone_id=None,
                display_language="en",
                password_hash=password_hash,
            )
        gang = Gang(name=crew.name, foreman_id=foreman_id)
        ctx.session.add(gang)
        ctx.session.flush()
        ctx.gang_id[crew.name] = gang.id

    for index, w in enumerate(ctx.workers):
        title = catalog.JOB_TITLES[ctx.crew_by_name[w.crew].activity]
        pid = _person_row(
            ctx,
            employer_id=ctx.employer_id[w.employer],
            first_name=w.first_name,
            last_name=w.last_name,
            email=f"{w.email_local}@{catalog.EMAIL_DOMAIN}",
            role="worker",
            job_title=title,
            hire_date=w.hire_date,
            site_arrival_date=w.arrival_date,
            induction=w.induction,
            camp_zone_id=ctx.zone_id[w.camp] if w.camp else None,
            display_language=w.display_language,
            password_hash=password_hash,
        )
        ctx.person_id[index] = pid
        if w.key:
            ctx.key_person["arjun.thapa"] = pid
        for code in w.competencies:
            ctx.add(
                PersonCompetency,
                person_id=pid,
                competency_id=ctx.competency_id[code],
                valid_until=date(2027, 6, 30) if code != "CONFINED_SPACE" else date(2026, 12, 31),
            )
        for course, done in w.courses.items():
            ctx.add(TrainingRecord, person_id=pid, course_code=course, completed_on=done)


def _roster(ctx: Ctx) -> None:
    rng = ctx.rng
    members: dict[str, list[int]] = {}
    for index, w in enumerate(ctx.workers):
        members.setdefault(w.crew, []).append(index)

    for day in roster_days():
        for kind in (ShiftKind.DAY, ShiftKind.NIGHT):
            start, end = shift_window(day, kind)
            shift = Shift(date=day, kind=kind, start_at=start, end_at=end)
            ctx.session.add(shift)
            ctx.session.flush()
            ctx.shift_id[(day, kind.value)] = shift.id

    for crew in ctx.crews:
        gang_id = ctx.gang_id[crew.name]
        for day in roster_days():
            letter = crew.pattern[((day - ROSTER_START).days + crew.phase) % len(crew.pattern)]
            if letter == "O":
                continue
            kind = ShiftKind.DAY if letter == "D" else ShiftKind.NIGHT
            start, _ = shift_window(day, kind)
            shift_id = ctx.shift_id[(day, kind.value)]
            story_window = crew.name == "Deck Gang 3" and day >= STORY_DATE - timedelta(days=3)
            for index in members[crew.name]:
                w = ctx.workers[index]
                pid = ctx.person_id[index]
                if w.hire_date > day:
                    continue
                past = start < CLOCK
                # Rostered either way; a sick worker keeps the roster slot and logs an absence.
                # The extended-night lashers keep a clean run in the fortnight before the
                # story night, so their roster-defined group is the one in the concept doc.
                protected = w.cohort == "exp_nights" and day >= STORY_DATE - timedelta(days=16)
                absent = past and not story_window and not protected and rng.random() < 0.02
                if absent:
                    ctx.add(Absence, person_id=pid, date=day, kind="sickness")
                activity = crew.activity
                if w.cohort == "recent_arrival":
                    # New arrivals start on ground work while they get used to the heat.
                    activity = "TWIST_GROUND"
                elif crew.alt_activity and not story_window and rng.random() < 0.12:
                    activity = crew.alt_activity
                ctx.add(
                    Assignment,
                    shift_id=shift_id,
                    person_id=pid,
                    activity_id=ctx.activity_id[activity],
                    gang_id=gang_id,
                    zone_id=ctx.zone_id[crew.zone],
                    source=AssignmentSource.ROSTER,
                )
                ctx.worked[pid].append((day, kind.value, crew.zone, activity))
                if past and not absent and rng.random() < 0.85:
                    _checkin(ctx, pid, shift_id, start, kind)


def _checkin(ctx: Ctx, pid: int, shift_id: int, start: datetime, kind: ShiftKind) -> None:
    r = ctx.rng.random()
    if kind == ShiftKind.NIGHT:
        band = (
            "under_5" if r < 0.07 else "5_to_6" if r < 0.22 else "6_to_7" if r < 0.6 else "7_plus"
        )
    else:
        band = (
            "under_5" if r < 0.04 else "5_to_6" if r < 0.13 else "6_to_7" if r < 0.5 else "7_plus"
        )
    f = ctx.rng.random()
    feeling = Feeling.UNWELL if f < 0.004 else Feeling.TIRED if f < 0.10 else Feeling.GOOD
    ctx.add(
        CheckIn,
        person_id=pid,
        shift_id=shift_id,
        at=start - timedelta(minutes=int(10 + ctx.rng.integers(0, 25))),
        sleep_hours_band=band,
        feeling=feeling,
        hydration_ok=bool(ctx.rng.random() > 0.05),
    )


def _fix_story_checkins(ctx: Ctx) -> None:
    """Arjun checked in for every past shift; two of his last ten followed short sleep."""
    arjun = ctx.key_person["arjun.thapa"]
    past = sorted(
        (d, k) for d, k, _, _ in ctx.worked[arjun] if shift_window(d, ShiftKind(k))[0] < CLOCK
    )
    short = {past[-8], past[-4]}
    rows = [r for r in ctx.rows[CheckIn] if r["person_id"] != arjun]
    for d, k in past:
        start, _ = shift_window(d, ShiftKind(k))
        rows.append(
            {
                "person_id": arjun,
                "shift_id": ctx.shift_id[(d, k)],
                "at": start - timedelta(minutes=18),
                "sleep_hours_band": "5_to_6" if (d, k) in short else "6_to_7",
                "feeling": Feeling.GOOD,
                "hydration_ok": True,
            }
        )
    ctx.rows[CheckIn] = rows


VESSELS = [
    "MV Coral Meridian",
    "MV Gulf Lantern",
    "MV Pearl Navigator",
    "MV Desert Falcon",
    "MV Azure Tide",
    "MV Amber Crest",
    "MV Jade Horizon",
    "MV Northern Dhow",
    "MV Silver Monsoon",
    "MV Dune Voyager",
    "MV Cedar Wind",
    "MV Ocean Saffron",
    "MV Blue Oryx",
    "MV Harbour Star",
    "MV Copper Gale",
    "MV Indigo Reef",
]


def _vessels_and_permits(ctx: Ctx) -> None:
    rng = ctx.rng
    story_arrive = datetime(2026, 7, 29, 14, 0)
    calls: list[tuple[str, int, datetime, datetime]] = []
    for berth in range(1, 5):
        zone = ctx.zone_id[f"Berth {berth}"]
        t = datetime(2026, 4, 29, int(rng.integers(0, 24)))
        while t < datetime(2026, 7, 31):
            length = timedelta(hours=int(rng.integers(26, 44)))
            if berth == 2 and t + length > story_arrive - timedelta(hours=6):
                break
            busy = {name for name, _, a, d in calls if a < t + length and d > t}
            free = [v for v in VESSELS if v not in busy]
            calls.append((ctx.pick(free), zone, t, t + length))
            t = t + length + timedelta(hours=int(rng.integers(5, 28)))
    calls.append(
        ("MV Saffron Horizon", ctx.zone_id["Berth 2"], story_arrive, datetime(2026, 7, 31, 2, 0))
    )
    for name, zone, arrive, depart in calls:
        ctx.add(
            VesselCall,
            vessel_name=name,
            berth_zone_id=zone,
            arrives_at=arrive,
            departs_at=depart,
            moves_planned=int((depart - arrive).total_seconds() // 3600 * 28),
        )

    issuer = ctx.key_person["priya.raman"]
    crews_at = {
        (d, k, zone_name, activity)
        for worked in ctx.worked.values()
        for d, k, zone_name, activity in worked
    }
    seq: dict[tuple[date, str], int] = {}
    for day in roster_days():
        for kind in (ShiftKind.DAY, ShiftKind.NIGHT):
            start, end = shift_window(day, kind)
            shift_id = ctx.shift_id[(day, kind.value)]
            for name, zone, arrive, depart in calls:
                if not (arrive < end and depart > start):
                    continue
                for activity in ("LASH_DECK", "QC_OPS", "MOORING", "HOLD_CONFINED"):
                    berth_name = next(n for n, i in ctx.zone_id.items() if i == zone)
                    if (day, kind.value, berth_name, activity) not in crews_at:
                        continue  # a permit only exists where a crew does that work
                    key = (day, kind.value)
                    seq[key] = seq.get(key, 0) + 1
                    number = f"PTW-{day:%y%m%d}-{kind.value[0].upper()}-{seq[key]:02d}"
                    if start < CLOCK - timedelta(hours=12):
                        status = PermitStatus.CLOSED
                    elif start < CLOCK + timedelta(hours=2):
                        status = PermitStatus.ISSUED
                    else:
                        status = PermitStatus.REQUESTED
                    permit = Permit(
                        number=number,
                        activity_id=ctx.activity_id[activity],
                        zone_id=zone,
                        shift_id=shift_id,
                        status=status,
                        issuer_id=issuer if status != PermitStatus.REQUESTED else None,
                    )
                    ctx.session.add(permit)
                    ctx.session.flush()
                    if start - timedelta(hours=10) > CLOCK:
                        continue  # requested after the site clock: not in the record yet
                    ctx.add(
                        PermitEvent,
                        permit_id=permit.id,
                        at=start - timedelta(hours=10),
                        kind="requested",
                        text=f"Requested for {name}.",
                        actor_id=None,
                    )
                    if status != PermitStatus.REQUESTED and start - timedelta(minutes=40) <= CLOCK:
                        ctx.add(
                            PermitEvent,
                            permit_id=permit.id,
                            at=start - timedelta(minutes=40),
                            kind="issued",
                            text="Issued after the pre-start check.",
                            actor_id=issuer,
                        )
                    if status == PermitStatus.CLOSED:
                        ctx.add(
                            PermitEvent,
                            permit_id=permit.id,
                            at=end,
                            kind="closed",
                            text="Work complete, area handed back.",
                            actor_id=issuer,
                        )
