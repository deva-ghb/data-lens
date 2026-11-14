"""Regression tests for the batch A review findings (C1, I1 to I9 and selected minors)."""

from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import set_site_now
from app.engine.crew_rules import CrewMember
from app.engine.montecarlo import split_risk
from app.engine.run import run_scores
from app.engine.score import score
from app.engine.swaps import keeps_crew_rules
from app.engine.weights import load_weights
from app.models import (
    Activity,
    Assignment,
    AssignmentScore,
    CheckIn,
    FitnessOutcome,
    NearMiss,
    PermitEvent,
    Person,
    Shift,
    SiteClock,
    Zone,
)
from app.models.health import FitnessDecision
from app.models.records import RecordStatus
from app.models.roster import Feeling, ShiftKind
from app.models.scores import ConditionsSource, RunKind, Tier

ARJUN = "arjun.thapa@mirsalterminals.com"


def _night(session: Session) -> Shift:
    return session.scalars(
        select(Shift).where(Shift.date == date(2026, 7, 29), Shift.kind == ShiftKind.NIGHT)
    ).one()


def _arjun_assignment(session: Session) -> Assignment:
    person = session.scalars(select(Person).where(Person.email == ARJUN)).one()
    return session.scalars(
        select(Assignment).where(
            Assignment.person_id == person.id, Assignment.shift_id == _night(session).id
        )
    ).one()


def _score(session: Session, run_id: int, person_id: int) -> AssignmentScore:
    return session.scalars(
        select(AssignmentScore)
        .join(Assignment, Assignment.id == AssignmentScore.assignment_id)
        .where(AssignmentScore.run_id == run_id, Assignment.person_id == person_id)
    ).one()


def test_unshared_outcome_does_not_change_r_or_reasons(scenario: Session) -> None:
    weights = load_weights(scenario)
    assignment = _arjun_assignment(scenario)
    before = score(scenario, assignment.id, weights, ConditionsSource.SCENARIO)
    scenario.add(
        FitnessOutcome(
            person_id=assignment.person_id,
            decided_by=assignment.person_id,
            at=datetime(2026, 7, 27, 6),
            outcome=FitnessDecision.FIT_WITH_RESTRICTIONS,
            restriction_text="No work above the second tier.",
            share_with_employer=False,
        )
    )
    scenario.flush()
    after = score(scenario, assignment.id, weights, ConditionsSource.SCENARIO)
    assert before is not None and after is not None
    assert after.tier == Tier.UNKNOWN
    assert after.r == before.r
    reasons = " ".join(d["reason"] for d in after.drivers).lower()
    assert "cleared by the clinician" not in reasons
    assert "with restrictions" not in reasons


def test_rescore_after_shift_start_marks_missing_checkins_unknown(scenario: Session) -> None:
    """Kiran never checks in for the story night; the crews around him did."""
    set_site_now(scenario, datetime(2026, 7, 29, 16, 0), None)
    run = run_scores(scenario, _night(scenario).id, RunKind.MANUAL)
    kiran = scenario.scalars(select(Person).where(Person.email.startswith("kiran.shrestha@"))).one()
    assert _score(scenario, run.id, kiran.id).tier == Tier.UNKNOWN
    tiers = {
        s.tier
        for s in scenario.scalars(select(AssignmentScore).where(AssignmentScore.run_id == run.id))
    }
    assert Tier.FIT in tiers


def test_late_checkin_clears_unknown(scenario: Session) -> None:
    assignment = _arjun_assignment(scenario)
    scenario.add(
        CheckIn(
            person_id=assignment.person_id,
            shift_id=assignment.shift_id,
            at=datetime(2026, 7, 29, 15, 5),
            sleep_hours_band="6_to_7",
            feeling=Feeling.GOOD,
            hydration_ok=True,
        )
    )
    set_site_now(scenario, datetime(2026, 7, 29, 15, 20), None)
    run = run_scores(scenario, assignment.shift_id, RunKind.SHIFT_START)
    assert _score(scenario, run.id, assignment.person_id).tier == Tier.REASSIGN


def test_near_miss_logged_at_the_current_clock_moves_control(scenario: Session) -> None:
    assignment = _arjun_assignment(scenario)
    set_site_now(scenario, datetime(2026, 7, 29, 10, 0), None)
    before = _score(
        scenario, run_scores(scenario, assignment.shift_id, RunKind.MANUAL).id, assignment.person_id
    )
    lash = scenario.scalars(select(Activity).where(Activity.code == "LASH_DECK")).one()
    berth = scenario.scalars(select(Zone).where(Zone.name == "Berth 2")).one()
    scenario.add(
        NearMiss(
            activity_id=lash.id,
            zone_id=berth.id,
            reported_by=None,
            at=datetime(2026, 7, 29, 9, 0),
            shift_kind=ShiftKind.DAY,
            text="Lashing bar dropped from the third tier.",
            potential_severity=4,
            status=RecordStatus.CLOSED,
        )
    )
    scenario.flush()
    after = _score(
        scenario, run_scores(scenario, assignment.shift_id, RunKind.MANUAL).id, assignment.person_id
    )
    assert after.control > before.control


def test_open_near_miss_does_not_move_control(scenario: Session) -> None:
    assignment = _arjun_assignment(scenario)
    before = _score(
        scenario,
        run_scores(scenario, assignment.shift_id, RunKind.EVENING).id,
        assignment.person_id,
    )
    lash = scenario.scalars(select(Activity).where(Activity.code == "LASH_DECK")).one()
    berth = scenario.scalars(select(Zone).where(Zone.name == "Berth 2")).one()
    scenario.add(
        NearMiss(
            activity_id=lash.id,
            zone_id=berth.id,
            reported_by=None,
            at=datetime(2026, 7, 28, 9, 0),
            shift_kind=ShiftKind.DAY,
            text="Unreviewed report.",
            potential_severity=3,
            status=RecordStatus.OPEN,
        )
    )
    scenario.flush()
    after = _score(
        scenario,
        run_scores(scenario, assignment.shift_id, RunKind.EVENING).id,
        assignment.person_id,
    )
    assert after.control == before.control


def test_not_today_does_not_last_thirty_days(scenario: Session) -> None:
    weights = load_weights(scenario)
    assignment = _arjun_assignment(scenario)
    scenario.add(
        FitnessOutcome(
            person_id=assignment.person_id,
            decided_by=assignment.person_id,
            at=datetime(2026, 7, 5, 6),
            outcome=FitnessDecision.NOT_TODAY,
            restriction_text=None,
            share_with_employer=True,
        )
    )
    scenario.flush()
    result = score(scenario, assignment.id, weights, ConditionsSource.SCENARIO)
    assert result is not None and result.tier != Tier.REFER


def test_swap_rejected_when_it_removes_the_only_experienced_worker() -> None:
    def member(i: int, group: str | None) -> CrewMember:
        return CrewMember(i, Tier.FIT, 1.0, 400, group, 5)

    crew = [member(1, "EXP_INHOUSE"), member(2, "NEW_CONTRACTOR"), member(3, None)]
    assert keeps_crew_rules(crew, moved_assignment_id=2, heat_tier=3) is True
    assert keeps_crew_rules(crew, moved_assignment_id=1, heat_tier=3) is False


def test_split_gives_conditions_a_real_share_on_the_story_night(scenario: Session) -> None:
    shift = _night(scenario)
    run_scores(scenario, shift.id, RunKind.EVENING)
    result = split_risk(scenario, shift.id, n=400)
    assert 0.3 <= result.conditions_share <= 0.9
    assert result.conditions_share + result.crew_share == pytest.approx(1.0)
    assert result.forecast_missing is False


def test_no_seeded_permit_event_after_the_clock(scenario: Session) -> None:
    clock = scenario.get_one(SiteClock, 1).now
    latest = max(scenario.scalars(select(PermitEvent.at)))
    assert latest <= clock
