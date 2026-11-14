from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.detector.detect import detect, evaluate_zone
from app.detector.open_record import open_warning
from app.models import WarningRecord, WarningStep, Zone
from app.models.warnings import WarningLevel


def _zone(session: Session, name: str) -> int:
    return session.scalars(select(Zone.id).where(Zone.name == name)).one()


def _signal_for(signals, zone_id):  # type: ignore[no-untyped-def]
    return next((s for s in signals if s.zone_id == zone_id), None)


def test_camp_c_raises_warning_on_27_july(scenario: Session) -> None:
    camp_c = _zone(scenario, "Camp Block C")
    on_27 = _signal_for(detect(scenario, date(2026, 7, 27)), camp_c)
    assert on_27 is not None and on_27.level == WarningLevel.WARNING
    assert on_27.classes_agreeing == {"clinical", "community"}
    feeds = {c.feed for c in on_27.contributions}
    assert {"CLINIC_VISITS", "CAMP_TICKETS"} <= feeds
    before = _signal_for(detect(scenario, date(2026, 7, 22)), camp_c)
    assert before is None or before.level != WarningLevel.WARNING


def test_single_class_never_above_watch(scenario: Session) -> None:
    camp_c = _zone(scenario, "Camp Block C")
    only_tickets = _signal_for(
        detect(scenario, date(2026, 7, 27), feeds_off=frozenset({"CLINIC_VISITS"})), camp_c
    )
    assert only_tickets is not None
    assert only_tickets.level == WarningLevel.WATCH


def test_clinic_feed_off_drops_one_level_and_is_named(scenario: Session) -> None:
    berth_3 = _zone(scenario, "Berth 3")
    normal = _signal_for(detect(scenario, date(2026, 6, 12)), berth_3)
    assert normal is not None and normal.level == WarningLevel.WARNING
    without_clinic = _signal_for(
        detect(scenario, date(2026, 6, 12), feeds_off=frozenset({"CLINIC_VISITS"})), berth_3
    )
    assert without_clinic is not None
    assert without_clinic.level == WarningLevel.WATCH
    assert "Clinic visits by syndrome" in without_clinic.late_feeds


def test_unlocated_records_count_to_district_only(scenario: Session) -> None:
    village = _zone(scenario, "Mirsal Village District")
    camp_a = _zone(scenario, "Camp Block A")
    district = evaluate_zone(scenario, village, date(2026, 7, 10))
    block = evaluate_zone(scenario, camp_a, date(2026, 7, 10))
    district_visits = sum(c.observed for c in district.all_series if c.feed == "CLINIC_VISITS")
    block_visits = sum(c.observed for c in block.all_series if c.feed == "CLINIC_VISITS")
    # The district total includes its blocks' located visits and the unlocated ones.
    assert district_visits > block_visits


def test_open_warning_creates_ten_steps(scenario: Session) -> None:
    camp_c = _zone(scenario, "Camp Block C")
    signal = _signal_for(detect(scenario, date(2026, 7, 27)), camp_c)
    assert signal is not None
    record = open_warning(scenario, signal)
    steps = scenario.scalars(
        select(WarningStep).where(WarningStep.warning_id == record.id).order_by(WarningStep.step)
    ).all()
    assert [s.step for s in steps] == list(range(1, 11))
    stored = scenario.get_one(WarningRecord, record.id)
    assert stored.evidence_json["classes"] == ["clinical", "community"]
