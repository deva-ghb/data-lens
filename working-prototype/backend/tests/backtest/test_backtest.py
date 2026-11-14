from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtest.harness import choose_action_line, run_backtest, sweep
from app.detector.detect import detect
from app.detector.series import clear_feed_index
from app.models import Feed, FeedReading, Setting, Zone
from app.models.feeds import FeedSource


def test_no_future_reads(scenario: Session) -> None:
    camp_c = scenario.scalars(select(Zone.id).where(Zone.name == "Camp Block C")).one()
    before = detect(scenario, date(2026, 7, 20))
    feed = scenario.scalars(select(Feed.id).where(Feed.code == "CLINIC_VISITS")).one()
    scenario.add(
        FeedReading(
            feed_id=feed,
            zone_id=camp_c,
            at=datetime(2026, 7, 22, 20),
            metric="heat_visits",
            value=500,
            source=FeedSource.SEEDED,
        )
    )
    scenario.flush()
    clear_feed_index(scenario)
    after = detect(scenario, date(2026, 7, 20))
    assert [(s.zone_id, s.level) for s in before] == [(s.zone_id, s.level) for s in after]


def test_all_four_events_found_with_lead_time_at_least_72h(scenario: Session) -> None:
    result = run_backtest(scenario, action_line=1.5)
    assert result.sensitivity == (4, 4)
    for code, hours in result.lead_time_hours.items():
        assert hours is not None and hours >= 72, code


def test_ppv_between_0_5_and_0_8(scenario: Session) -> None:
    result = run_backtest(scenario, action_line=1.5)
    assert 0.5 <= result.ppv <= 0.8
    assert result.false_alarms_per_30d > 0


def test_switching_off_clinic_feed_degrades_result(scenario: Session) -> None:
    full = run_backtest(scenario, action_line=1.5)
    without = run_backtest(scenario, action_line=1.5, feeds_off=frozenset({"CLINIC_VISITS"}))
    assert without.sensitivity[0] < full.sensitivity[0]
    assert "CLINIC_VISITS" in without.feeds_off


def test_sweep_and_choose_action_line_store_the_result(scenario: Session) -> None:
    results = sweep(scenario, [1.4, 1.5, 2.0])
    assert [r.action_line for r in results] == [1.4, 1.5, 2.0]
    chosen = choose_action_line(results)
    assert chosen in (1.4, 1.5, 2.0)
    stored = scenario.get(Setting, "backtest_last")
    assert stored is not None and stored.value["action_line"] == results[-1].action_line
    assert {"lead_time_hours", "ppv", "sensitivity", "latency_by_feed"} <= set(stored.value)
