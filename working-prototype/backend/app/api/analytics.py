"""Analytics: the back-test (validation) and impact on editable inputs."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.analytics.impact import ImpactInputs, impact
from app.api.common import SessionDep, require_role, require_scope
from app.backtest.harness import run_backtest, sweep
from app.detector.series import FEED_NAMES_FALLBACK, feed_index
from app.models import Person, Setting

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/validation")
def validation(
    session: SessionDep, user: Person = Depends(require_scope("aggregates"))
) -> dict[str, Any]:
    stored = session.get(Setting, "backtest_last")
    if stored is None:
        sweep(session)
        session.commit()
        stored = session.get_one(Setting, "backtest_last")
    feeds = feed_index(session).feeds
    value = dict(stored.value)
    value["feed_names"] = {code: f.name for code, f in feeds.items()} or FEED_NAMES_FALLBACK
    return value


class BacktestBody(BaseModel):
    action_line: float = Field(1.5, ge=1.0, le=3.0)
    feeds_off: list[str] = []


@router.post("/backtest")
def backtest(
    body: BacktestBody, session: SessionDep, user: Person = Depends(require_role("hse_head"))
) -> dict[str, Any]:
    result = run_backtest(session, body.action_line, frozenset(body.feeds_off))
    return result.as_json()


@router.get("/impact")
def impact_default(user: Person = Depends(require_scope("aggregates"))) -> dict[str, Any]:
    return impact(ImpactInputs())


class ImpactBody(BaseModel):
    lti_per_year: float = Field(40, ge=0, le=100_000)
    hot_share: float = Field(0.4, ge=0, le=1)
    night_share: float = Field(0.2, ge=0, le=1)
    acted_on: float = Field(0.7, ge=0, le=1)
    effectiveness: float = Field(0.5, ge=0, le=1)
    workdays_per_injury: float = Field(20, ge=0, le=365)


@router.post("/impact")
def impact_custom(
    body: ImpactBody, user: Person = Depends(require_scope("aggregates"))
) -> dict[str, Any]:
    return impact(ImpactInputs(**body.model_dump()))
