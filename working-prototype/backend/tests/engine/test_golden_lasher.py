"""The concept doc's walkthrough, reproduced by the engine from raw seeded records."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.score import score
from app.engine.weights import load_weights
from app.models import Assignment, Person, Shift
from app.models.roster import ShiftKind
from app.models.scores import ConditionsSource, Tier


def test_lasher_reproduces_walkthrough(scenario: Session) -> None:
    marco = scenario.scalars(
        select(Person).where(Person.email == "marco.villanueva@mirsalterminals.com")
    ).one()
    assignment = scenario.scalars(
        select(Assignment)
        .join(Shift, Shift.id == Assignment.shift_id)
        .where(
            Assignment.person_id == marco.id,
            Shift.date == date(2026, 7, 29),
            Shift.kind == ShiftKind.NIGHT,
        )
    ).one()
    weights = load_weights(scenario, "v0")
    result = score(scenario, assignment.id, weights, ConditionsSource.SCENARIO)
    assert result is not None
    assert result.intrinsic == 1.0
    assert result.control == pytest.approx(1.15, abs=0.02)
    assert result.condition == pytest.approx(1.25, abs=0.02)
    assert result.profile == pytest.approx(1.35, abs=0.02)
    assert result.r == pytest.approx(1.94, abs=0.03)
    assert result.tier == Tier.REASSIGN
    assert result.group_step_limited is False
