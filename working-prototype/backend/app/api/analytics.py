"""Analytics: the back-test (validation) and impact on editable inputs."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.analytics.impact import ImpactInputs, impact
from app.api.common import SessionDep, require_scope
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
    action_line: float = 1.5
    feeds_off: list[str] = []


@router.post("/backtest")
def backtest(
    body: BacktestBody, session: SessionDep, user: Person = Depends(require_scope("aggregates"))
) -> dict[str, Any]:
    result = run_backtest(session, body.action_line, frozenset(body.feeds_off))
    return result.as_json()


@router.get("/impact")
def impact_default(user: Person = Depends(require_scope("aggregates"))) -> dict[str, Any]:
    return impact(ImpactInputs())


class ImpactBody(BaseModel):
    lti_per_year: float = 40
    hot_share: float = 0.4
    night_share: float = 0.2
    acted_on: float = 0.7
    effectiveness: float = 0.5
    workdays_per_injury: float = 20


@router.post("/impact")
def impact_custom(
    body: ImpactBody, user: Person = Depends(require_scope("aggregates"))
) -> dict[str, Any]:
    return impact(ImpactInputs(**body.model_dump()))
