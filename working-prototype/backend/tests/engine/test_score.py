from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import set_site_now
from app.engine.score import limit_group_step, score, tier_for
from app.engine.weights import load_weights
from app.models import Activity, Assignment, CheckIn, Person, Shift
from app.models.roster import Feeling, ShiftKind
from app.models.scores import ConditionsSource, Tier


def _night_29(session: Session) -> Shift:
    return session.scalars(
        select(Shift).where(Shift.date == date(2026, 7, 29), Shift.kind == ShiftKind.NIGHT)
    ).one()


def _assignment(session: Session, email: str) -> Assignment:
    person = session.scalars(select(Person).where(Person.email == email)).one()
    return session.scalars(
        select(Assignment).where(
            Assignment.person_id == person.id, Assignment.shift_id == _night_29(session).id
        )
    ).one()


MARCO = "marco.villanueva@mirsalterminals.com"


def test_grade_2_not_scored_per_person(scenario: Session) -> None:
    weights = load_weights(scenario)
    inspect_id = scenario.scalars(
        select(Activity.id).where(Activity.code == "CONTAINER_INSPECT")
    ).one()
    assignment = scenario.scalars(
        select(Assignment).where(Assignment.activity_id == inspect_id).limit(1)
    ).one()
    assert score(scenario, assignment.id, weights, ConditionsSource.SCENARIO) is None


def test_grade_3_thresholds_1_5_and_2_4(scenario: Session) -> None:
    weights = load_weights(scenario)
    assert tier_for(3, 1.49, weights) == Tier.FIT
    assert tier_for(3, 1.5, weights) == Tier.FIT_WITH_CONTROLS
    assert tier_for(3, 2.39, weights) == Tier.FIT_WITH_CONTROLS
    assert tier_for(3, 2.4, weights) == Tier.REASSIGN
    assert tier_for(5, 1.3, weights) == Tier.FIT_WITH_CONTROLS
    assert tier_for(5, 1.9, weights) == Tier.REASSIGN


def test_group_factor_moves_tier_at_most_one_step() -> None:
    assert limit_group_step(Tier.REASSIGN, Tier.FIT) == (Tier.FIT_WITH_CONTROLS, True)
    assert limit_group_step(Tier.REASSIGN, Tier.FIT_WITH_CONTROLS) == (Tier.REASSIGN, False)
    assert limit_group_step(Tier.FIT_WITH_CONTROLS, Tier.FIT) == (Tier.FIT_WITH_CONTROLS, False)
    # A protective group (multiplier below 1) can lower the tier by one step at most.
    assert limit_group_step(Tier.FIT, Tier.REASSIGN) == (Tier.FIT_WITH_CONTROLS, True)


def test_unwell_checkin_gives_refer(scenario: Session) -> None:
    weights = load_weights(scenario)
    assignment = _assignment(scenario, MARCO)
    scenario.add(
        CheckIn(
            person_id=assignment.person_id,
            shift_id=assignment.shift_id,
            at=datetime(2026, 7, 29, 14, 40),
            sleep_hours_band="6_to_7",
            feeling=Feeling.UNWELL,
            hydration_ok=True,
        )
    )
    scenario.flush()
    # Before the shift starts the engine cannot see the check-in.
    early = score(scenario, assignment.id, weights, ConditionsSource.SCENARIO)
    assert early is not None and early.tier == Tier.REASSIGN
    set_site_now(scenario, datetime(2026, 7, 29, 15, 0), None)
    result = score(scenario, assignment.id, weights, ConditionsSource.SCENARIO)
    assert result is not None and result.tier == Tier.REFER


def test_no_checkin_at_shift_start_is_unknown(scenario: Session) -> None:
    weights = load_weights(scenario)
    assignment = _assignment(scenario, MARCO)
    result = score(
        scenario, assignment.id, weights, ConditionsSource.SCENARIO, require_checkin=True
    )
    assert result is not None and result.tier == Tier.UNKNOWN


def test_drivers_sorted_by_contribution_with_source_and_freshness(scenario: Session) -> None:
    weights = load_weights(scenario)
    result = score(scenario, _assignment(scenario, MARCO).id, weights, ConditionsSource.SCENARIO)
    assert result is not None
    contributions = [d["contribution"] for d in result.drivers]
    assert contributions == sorted(contributions, reverse=True)
    for driver in result.drivers:
        assert {"layer", "name", "contribution", "source", "freshness_hours", "reason"} <= set(
            driver
        )
    names = [d["name"] for d in result.drivers[:4]]
    assert "safety_behaviour" in names
