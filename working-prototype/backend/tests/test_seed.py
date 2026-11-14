"""The seeded scenario: raw history only, deterministic, and true to the walkthrough."""

from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import db
from app.models import (
    Activity,
    Assignment,
    AssignmentScore,
    CampTicket,
    ClinicVisit,
    Employer,
    Feed,
    FeedReading,
    FitnessOutcome,
    Gang,
    NearMiss,
    Observation,
    Person,
    Role,
    ScoreRun,
    Shift,
    TrainingRecord,
    VesselCall,
    WarningRecord,
    Zone,
)
from app.models.records import ObservationKind
from app.models.roster import ShiftKind
from seed.build import build_database


@pytest.fixture(scope="module")
def seeded_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("seeded") / "seeded.db"
    build_database(path)
    return path


@pytest.fixture
def seeded(seeded_path: Path) -> Iterator[Session]:
    engine = db.make_engine(f"sqlite:///{seeded_path}")
    with Session(engine) as session:
        yield session
    engine.dispose()


def _activity_id(session: Session, code: str) -> int:
    return session.scalars(select(Activity.id).where(Activity.code == code)).one()


def _arjun(session: Session) -> Person:
    return session.scalars(
        select(Person).where(Person.email == "arjun.thapa@mirsalterminals.com")
    ).one()


def test_seed_is_deterministic(seeded_path: Path, tmp_path: Path) -> None:
    second = tmp_path / "again.db"
    build_database(second)

    def snapshot(path: Path) -> tuple[list[int], list[tuple]]:
        engine = db.make_engine(f"sqlite:///{path}")
        with Session(engine) as session:
            counts = [
                session.scalar(select(func.count()).select_from(m))
                for m in (Person, Assignment, Observation, FeedReading, ClinicVisit)
            ]
            rows = session.execute(
                select(
                    Observation.activity_id,
                    Observation.person_id,
                    Observation.at,
                    Observation.kind,
                    Observation.text,
                )
                .order_by(Observation.id)
                .limit(50)
            ).all()
        engine.dispose()
        return counts, [tuple(r) for r in rows]

    assert snapshot(seeded_path) == snapshot(second)


def test_four_hundred_workers_three_employers(seeded: Session) -> None:
    workers = seeded.scalar(
        select(func.count()).select_from(Person).where(Person.role == Role.WORKER)
    )
    assert workers == 400
    shares = dict(
        seeded.execute(
            select(Employer.name, func.count(Person.id))
            .join(Person, Person.employer_id == Employer.id)
            .where(Person.role == Role.WORKER)
            .group_by(Employer.name)
        ).all()
    )
    assert shares["Mirsal Terminals"] == pytest.approx(180, abs=12)
    assert shares["Sahel Marine Services"] == pytest.approx(120, abs=12)
    assert shares["Bayan Manpower Contracting"] == pytest.approx(100, abs=12)
    for email in (
        "hessa.almansoori@mirsalterminals.com",
        "layla.haddad@mirsalterminals.com",
        "sara.ibrahim@mirsalterminals.com",
    ):
        assert seeded.scalar(select(Person).where(Person.email == email)) is not None


def test_every_feed_has_90_days(seeded: Session) -> None:
    for feed in seeded.scalars(select(Feed)):
        first, last = seeded.execute(
            select(func.min(FeedReading.at), func.max(FeedReading.at)).where(
                FeedReading.feed_id == feed.id
            )
        ).one()
        assert first is not None, feed.code
        assert first <= datetime(2026, 5, 1, 23, 59), feed.code
        assert last >= datetime(2026, 7, 27, 20), feed.code  # local midnight, 28 July


def test_uabc_history_spans_12_months(seeded: Session) -> None:
    first, last = seeded.execute(select(func.min(Observation.at), func.max(Observation.at))).one()
    assert first < datetime(2025, 8, 15)
    assert last >= datetime(2026, 7, 1)


def test_no_derived_tables_populated(seeded: Session) -> None:
    assert seeded.scalar(select(func.count()).select_from(ScoreRun)) == 0
    assert seeded.scalar(select(func.count()).select_from(AssignmentScore)) == 0
    # The seed replays the detector over the history, as the live system would have run.
    # Past warnings are closed with an outcome; only Camp Block C is still open.
    open_zones = seeded.scalars(
        select(Zone.name)
        .join(WarningRecord, WarningRecord.zone_id == Zone.id)
        .where(WarningRecord.closed_at.is_(None))
    ).all()
    assert open_zones == ["Camp Block C"]


def test_saffron_horizon_berths_at_berth_2_on_29_july(seeded: Session) -> None:
    call = seeded.scalars(
        select(VesselCall).where(VesselCall.vessel_name == "MV Saffron Horizon")
    ).one()
    berth = seeded.get(Zone, call.berth_zone_id)
    assert berth is not None and berth.name == "Berth 2"
    assert call.arrives_at <= datetime(2026, 7, 29, 15, 0) < call.departs_at


def test_lash_deck_uabc_counts_match_story(seeded: Session) -> None:
    window_start = datetime(2025, 7, 29)
    lash = _activity_id(seeded, "LASH_DECK")
    kinds = dict(
        seeded.execute(
            select(Observation.kind, func.count())
            .where(Observation.at >= window_start)
            .where(Observation.activity_id == lash)
            .where(Observation.kind != ObservationKind.SAFE)
            .group_by(Observation.kind)
        ).all()
    )
    assert kinds == {
        ObservationKind.UNSAFE_ACT: 11,
        ObservationKind.UNSAFE_BEHAVIOUR: 6,
        ObservationKind.UNSAFE_CONDITION: 7,
    }
    near_misses = seeded.scalars(select(NearMiss).where(NearMiss.activity_id == lash)).all()
    assert len(near_misses) == 3
    lash_unsafe_shifts = seeded.scalars(
        select(Observation.shift_kind)
        .where(Observation.activity_id == lash)
        .where(Observation.kind != ObservationKind.SAFE)
    ).all()
    assert set(lash_unsafe_shifts) == {ShiftKind.NIGHT}
    assert {n.shift_kind for n in near_misses} == {ShiftKind.NIGHT}


def test_arjun_third_night_on_29_july(seeded: Session) -> None:
    arjun = _arjun(seeded)
    kinds = {}
    for day in (26, 27, 28, 29):
        shift_kind = seeded.scalar(
            select(Shift.kind)
            .join(Assignment, Assignment.shift_id == Shift.id)
            .where(Assignment.person_id == arjun.id, Shift.date == date(2026, 7, day))
        )
        kinds[day] = shift_kind
    assert kinds == {26: None, 27: ShiftKind.NIGHT, 28: ShiftKind.NIGHT, 29: ShiftKind.NIGHT}
    activity = seeded.scalar(
        select(Assignment)
        .join(Shift, Assignment.shift_id == Shift.id)
        .where(Assignment.person_id == arjun.id, Shift.date == date(2026, 7, 29))
    )
    assert activity is not None and activity.activity_id == _activity_id(seeded, "LASH_DECK")
    courses = set(
        seeded.scalars(
            select(TrainingRecord.course_code).where(TrainingRecord.person_id == arjun.id)
        )
    )
    assert "HEIGHT_REFRESHER" not in courses
    assert "CONTRACTOR_INDUCTION" in courses


def test_arjun_short_sleep_in_two_of_last_ten_checkins(seeded: Session) -> None:
    from app.models import CheckIn

    arjun = _arjun(seeded)
    last_ten = seeded.scalars(
        select(CheckIn).where(CheckIn.person_id == arjun.id).order_by(CheckIn.at.desc()).limit(10)
    ).all()
    assert len(last_ten) == 10
    short = [c for c in last_ten if c.sleep_hours_band in ("under_5", "5_to_6")]
    assert len(short) == 2


def test_forecast_wbgt_34_at_noon_29_july(seeded: Session) -> None:
    from app.feeds.wbgt import estimate_wbgt

    noon_utc = datetime(2026, 7, 29, 8, 0)
    readings = dict(
        seeded.execute(
            select(FeedReading.metric, FeedReading.value)
            .join(Feed, Feed.id == FeedReading.feed_id)
            .where(Feed.code == "WEATHER", FeedReading.at == noon_utc)
        ).all()
    )
    wbgt = estimate_wbgt(readings["temp_c"], readings["rh_pct"], readings["radiation_wm2"])
    assert wbgt == pytest.approx(34.0, abs=0.3)


def test_camp_c_tickets_11_of_40(seeded: Session) -> None:
    camp_c = seeded.scalars(select(Zone).where(Zone.name == "Camp Block C")).one()
    tickets = seeded.scalars(
        select(CampTicket).where(
            CampTicket.zone_id == camp_c.id,
            CampTicket.kind == "cooling_failure",
            CampTicket.opened_at >= datetime(2026, 7, 24),
            CampTicket.closed_at.is_(None),
        )
    ).all()
    assert sum(t.units_affected for t in tickets) == 11
    assert {t.units_total for t in tickets} == {40}


def test_camp_c_clinic_heat_visits_about_double_baseline(seeded: Session) -> None:
    camp_c = seeded.scalars(select(Zone).where(Zone.name == "Camp Block C")).one()

    def heat_visits(start: datetime, days: int) -> float:
        count = seeded.scalar(
            select(func.count())
            .select_from(ClinicVisit)
            .where(
                ClinicVisit.zone_id == camp_c.id,
                ClinicVisit.syndrome == "heat",
                ClinicVisit.at >= start,
                ClinicVisit.at < start + timedelta(days=days),
            )
        )
        return count / days

    event = heat_visits(datetime(2026, 7, 25), 4)
    baseline = heat_visits(datetime(2026, 6, 27), 28)
    assert 1.8 <= event / baseline <= 2.4


def test_gang_mate_cleared_by_clinician_on_19_july(seeded: Session) -> None:
    arjun = _arjun(seeded)
    gang_id = seeded.scalar(
        select(Assignment.gang_id).where(Assignment.person_id == arjun.id).limit(1)
    )
    gang = seeded.get(Gang, gang_id)
    assert gang is not None and gang.name == "Deck Gang 3"
    outcome = seeded.scalars(
        select(FitnessOutcome)
        .join(Assignment, Assignment.person_id == FitnessOutcome.person_id)
        .where(Assignment.gang_id == gang_id)
        .where(func.date(FitnessOutcome.at) == "2026-07-19")
    ).first()
    assert outcome is not None and outcome.person_id != arjun.id
