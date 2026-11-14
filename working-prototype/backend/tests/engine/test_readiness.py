from dataclasses import fields
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.readiness import ReadinessInputs, gather_inputs, readiness
from app.engine.weights import load_weights
from app.models import Person, Shift
from app.models.roster import ShiftKind

LASH_HAZARDS = ["FALL_HEIGHT", "DROPPED_LOAD", "HEAT_ILLNESS", "MANUAL_HANDLING"]


def _inputs(**overrides: object) -> ReadinessInputs:
    values: dict[str, object] = {
        "person_id": 1,
        "consecutive_nights": 0,
        "acclimatisation_days": 400,
        "short_sleep_checkins_last10": 0,
        "latest_checkin": None,
        "competencies_current": {"LASHING"},
        "training_missing": set(),
        "group_code": None,
        "group_multiplier": 1.0,
        "fitness_outcome": None,
        "lab_flags": 0,
        "unwell_event": False,
    }
    values.update(overrides)
    return ReadinessInputs(**values)  # type: ignore[arg-type]


def test_inputs_dataclass_has_no_protected_fields() -> None:
    names = {f.name for f in fields(ReadinessInputs)}
    for word in ("nationality", "origin", "religion", "ethnicity", "language", "name"):
        assert not any(word in n for n in names), word


def test_third_night_fatigue_multiplier(scenario: Session) -> None:
    weights = load_weights(scenario)
    factors = readiness(_inputs(consecutive_nights=3), weights)
    assert factors["fatigue"].multiplier == pytest.approx(1.12)
    with_sleep = readiness(_inputs(consecutive_nights=3, short_sleep_checkins_last10=2), weights)
    assert with_sleep["fatigue"].multiplier == pytest.approx(1.12 * 1.06)


def test_fourth_night_uses_published_seed(scenario: Session) -> None:
    weights = load_weights(scenario)
    assert readiness(_inputs(consecutive_nights=5), weights)["fatigue"].multiplier == 1.36


def test_group_multiplier_capped_at_1_6(scenario: Session) -> None:
    weights = load_weights(scenario)
    factors = readiness(_inputs(group_code="NEW_CONTRACTOR", group_multiplier=2.3), weights)
    assert factors["safety_behaviour"].multiplier == 1.6


def test_missing_checkin_lowers_confidence_and_marks_acute_unknown(scenario: Session) -> None:
    weights = load_weights(scenario)
    factors = readiness(_inputs(), weights)
    assert factors["acute"].multiplier == 1.0
    assert factors["acute"].confidence < 0.6
    assert "No check-in" in factors["acute"].reason


def test_reason_text_uses_work_terms_not_diagnosis(scenario: Session) -> None:
    weights = load_weights(scenario)
    factors = readiness(_inputs(lab_flags=2, consecutive_nights=3), weights)
    for factor in factors.values():
        lowered = factor.reason.lower()
        for word in ("creatinine", "hba1c", "sodium", "lab", "diagnos", "syndrome"):
            assert word not in lowered


def test_arjun_inputs_from_the_seed(scenario: Session) -> None:
    arjun = scenario.scalars(
        select(Person).where(Person.email == "arjun.thapa@mirsalterminals.com")
    ).one()
    shift = scenario.scalars(
        select(Shift).where(Shift.date == date(2026, 7, 29), Shift.kind == ShiftKind.NIGHT)
    ).one()
    inputs = gather_inputs(scenario, arjun.id, shift.id)
    assert inputs.consecutive_nights == 3
    assert inputs.short_sleep_checkins_last10 == 2
    assert inputs.group_code == "NEW_CONTRACTOR"
    assert inputs.group_multiplier == pytest.approx(1.6, abs=0.05)
    assert "HEIGHT_REFRESHER" in inputs.training_missing
    assert inputs.latest_checkin is None
    factors = readiness(inputs, load_weights(scenario))
    assert set(factors) == {
        "fatigue",
        "heat_strain",
        "physical",
        "acute",
        "safety_behaviour",
        "competency",
    }
    assert LASH_HAZARDS
