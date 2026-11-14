"""Administration: the site clock (people and reset follow in the admin task)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.common import LOCAL, SessionDep, require_scope
from app.clock import set_site_now, site_now
from app.models import Person

router = APIRouter(prefix="/admin", tags=["admin"])


class ClockBody(BaseModel):
    now: datetime


@router.put("/clock")
def move_clock(
    body: ClockBody, session: SessionDep, user: Person = Depends(require_scope("admin"))
) -> dict[str, Any]:
    set_site_now(session, body.now.replace(tzinfo=None), user)
    session.commit()
    now = site_now(session)
    return {"site_now": now.isoformat(), "site_now_local": (now + LOCAL).isoformat()}
