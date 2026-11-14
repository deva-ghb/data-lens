from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.montecarlo import split_risk
from app.engine.run import run_scores
from app.models import Shift
from app.models.roster import ShiftKind
from app.models.scores import RunKind


def _night(session: Session) -> Shift:
    return session.scalars(
        select(Shift).where(Shift.date == date(2026, 7, 29), Shift.kind == ShiftKind.NIGHT)
    ).one()


def test_shares_sum_to_one(scenario: Session) -> None:
    shift = _night(scenario)
    run_scores(scenario, shift.id, RunKind.EVENING)
    result = split_risk(scenario, shift.id, n=500)
    assert result.conditions_share + result.crew_share == pytest.approx(1.0)
    assert result.p10 <= result.total_expected <= result.p90


def test_same_seed_same_result(scenario: Session) -> None:
    shift = _night(scenario)
    run_scores(scenario, shift.id, RunKind.EVENING)
    assert split_risk(scenario, shift.id, n=400, seed=7) == split_risk(
        scenario, shift.id, n=400, seed=7
    )


def test_hotter_forecast_raises_conditions_share(scenario: Session) -> None:
    shift = _night(scenario)
    run_scores(scenario, shift.id, RunKind.EVENING)
    calm = split_risk(scenario, shift.id, n=600, wbgt_sd=0.5)
    uncertain = split_risk(scenario, shift.id, n=600, wbgt_sd=3.0)
    assert uncertain.conditions_share > calm.conditions_share
