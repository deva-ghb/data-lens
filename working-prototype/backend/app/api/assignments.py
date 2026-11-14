"""Assignment risk: engine runs, the roster with tiers, the layer build, swaps and approval."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import LOCAL, SessionDep, require_scope
from app.clock import site_now
from app.engine.run import run_scores
from app.errors import ApiError
from app.models import Person, Shift
from app.models.roster import ShiftKind
from app.models.scores import ConditionsSource, RunKind

router = APIRouter(tags=["assignments"])


class RunBody(BaseModel):
    kind: str = "manual"
    shift_id: int | None = None
    conditions_source: str = "scenario"


@router.post("/runs", status_code=201)
def start_run(
    body: RunBody,
    session: SessionDep,
    user: Person = Depends(require_scope("site_tiers")),
) -> dict[str, Any]:
    try:
        kind = RunKind(body.kind)
        source = ConditionsSource(body.conditions_source)
    except ValueError:
        raise ApiError(422, "invalid_input", "Unknown run kind or conditions source.") from None
    shift = session.get(Shift, body.shift_id) if body.shift_id else default_shift(session, kind)
    if shift is None:
        raise ApiError(404, "not_found", "There is no shift to score.")
    run = run_scores(session, shift.id, kind, source, actor=user)
    session.commit()
    return {"run_id": run.id, "shift_id": shift.id}


def default_shift(session: Session, kind: RunKind) -> Shift | None:
    """The evening run scores tomorrow night's roster; other runs the shift now running,
    or the next one to start."""
    now = site_now(session)
    if kind == RunKind.EVENING:
        tomorrow = (now + LOCAL).date() + timedelta(days=1)
        return session.scalars(
            select(Shift).where(Shift.date == tomorrow, Shift.kind == ShiftKind.NIGHT)
        ).first()
    running = session.scalars(
        select(Shift).where(Shift.start_at <= now, Shift.end_at > now)
    ).first()
    return (
        running
        or session.scalars(
            select(Shift).where(Shift.start_at > now).order_by(Shift.start_at)
        ).first()
    )
