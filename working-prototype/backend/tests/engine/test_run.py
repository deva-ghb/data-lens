from datetime import date, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import set_site_now
from app.engine.groups import group_rates
from app.engine.learn import approve_weights, propose_weights_from_outcomes
from app.engine.run import run_scores
from app.engine.weights import load_weights
from app.models import (
    Activity,
    Assignment,
    AssignmentScore,
    NearMiss,
    Person,
    Shift,
    WarningRecord,
    Zone,
)
from app.models.records import RecordStatus
from app.models.roster import ShiftKind
from app.models.scores import RunKind, Tier
from app.models.warnings import WarningLevel, WarningOutcome, WarningStatus


def _night(session: Session) -> Shift:
    return session.scalars(
        select(Shift).where(Shift.date == date(2026, 7, 29), Shift.kind == ShiftKind.NIGHT)
    ).one()


def _arjun_score(session: Session, run_id: int) -> AssignmentScore:
    arjun = session.scalars(
        select(Person).where(Person.email == "arjun.thapa@mirsalterminals.com")
    ).one()
    return session.scalars(
        select(AssignmentScore)
        .join(Assignment, Assignment.id == AssignmentScore.assignment_id)
        .where(AssignmentScore.run_id == run_id, Assignment.person_id == arjun.id)
    ).one()


def test_evening_run_scores_every_graded_assignment_for_29_july_night(scenario: Session) -> None:
    shift = _night(scenario)
    run = run_scores(scenario, shift.id, RunKind.EVENING)
    graded = scenario.scalar(
        select(func.count())
        .select_from(Assignment)
        .join(Activity, Activity.id == Assignment.activity_id)
        .where(Assignment.shift_id == shift.id, Activity.grade >= 3)
    )
    scored = scenario.scalar(
        select(func.count()).select_from(AssignmentScore).where(AssignmentScore.run_id == run.id)
    )
    assert scored == graded
    assert _arjun_score(scenario, run.id).tier == Tier.REASSIGN


def test_worker_without_checkin_is_unknown_at_shift_start(scenario: Session) -> None:
    shift = _night(scenario)
    set_site_now(scenario, datetime(2026, 7, 29, 15, 0), None)
    run = run_scores(scenario, shift.id, RunKind.SHIFT_START)
    assert _arjun_score(scenario, run.id).tier == Tier.UNKNOWN


def test_group_rates_within_0_05_of_spec_table(scenario: Session) -> None:
    rates = group_rates(scenario, _night(scenario).start_at)
    expected = {
        "EXP_INHOUSE": (48, 0.8),
        "NEW_CONTRACTOR": (26, 1.6),
        "EXP_NIGHTS": (22, 1.3),
        "YARD_REFRESHED": (58, 0.9),
        "YARD_OVERDUE": (31, 1.4),
        "MOORING_ALL": (34, 1.0),
    }
    for code, (people, multiplier) in expected.items():
        assert rates[code].people == people, code
        assert rates[code].multiplier == pytest.approx(multiplier, abs=0.05), code


def test_confirmed_near_miss_raises_control_on_next_run(scenario: Session) -> None:
    shift = _night(scenario)
    before = _arjun_score(scenario, run_scores(scenario, shift.id, RunKind.EVENING).id).control
    lash = scenario.scalars(select(Activity).where(Activity.code == "LASH_DECK")).one()
    berth = scenario.scalars(select(Zone).where(Zone.name == "Berth 2")).one()
    scenario.add(
        NearMiss(
            activity_id=lash.id,
            zone_id=berth.id,
            reported_by=None,
            at=datetime(2026, 7, 28, 1, 0),
            shift_kind=ShiftKind.NIGHT,
            text="Bar slipped from a lasher's hands at the third tier.",
            potential_severity=4,
            status=RecordStatus.CLOSED,
        )
    )
    scenario.flush()
    after = _arjun_score(scenario, run_scores(scenario, shift.id, RunKind.MANUAL).id).control
    assert after > before


def test_proposed_weights_not_used_until_approved(scenario: Session) -> None:
    zone = scenario.scalars(select(Zone).where(Zone.name == "Camp Block B")).one()
    for day in (3, 10, 17):
        scenario.add(
            WarningRecord(
                opened_at=datetime(2026, 6, day),
                zone_id=zone.id,
                level=WarningLevel.WARNING,
                status=WarningStatus.CLOSED,
                outcome=WarningOutcome.FALSE_ALARM,
                closed_at=datetime(2026, 6, day + 2),
            )
        )
    scenario.flush()
    proposed = propose_weights_from_outcomes(scenario)
    assert proposed is not None and proposed.status == "proposed"
    assert load_weights(scenario).version == "v0"
    approve_weights(scenario, proposed.id, None)
    active = load_weights(scenario)
    assert active.version == proposed.version
    assert active.thresholds[5][0] > 1.3
