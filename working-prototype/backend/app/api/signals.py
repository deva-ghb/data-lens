"""Signals: the feeds, their class, cadence and freshness, and connecting a new feed."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.common import SessionDep, not_found, require_role, require_scope
from app.clock import site_now
from app.errors import ApiError
from app.feeds.csv_connect import ColumnMap, Proposal, confirm_mapping, propose_mapping
from app.models import Feed, FeedReading, Person, Setting
from app.models.feeds import FeedSource

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
def signals(
    session: SessionDep, user: Person = Depends(require_scope("aggregates", "admin"))
) -> dict[str, Any]:
    clock = site_now(session)
    real_now = datetime.now(UTC).replace(tzinfo=None)
    feeds = []
    for f in session.scalars(select(Feed).order_by(Feed.signal_class, Feed.name)):
        latest_seeded = session.scalar(
            select(func.max(FeedReading.at)).where(
                FeedReading.feed_id == f.id,
                FeedReading.source != FeedSource.LIVE,
                FeedReading.at <= clock,
            )
        )
        latest_live = session.scalar(
            select(func.max(FeedReading.at)).where(
                FeedReading.feed_id == f.id, FeedReading.source == FeedSource.LIVE
            )
        )
        count = session.scalar(
            select(func.count()).select_from(FeedReading).where(FeedReading.feed_id == f.id)
        )
        allowed = timedelta(minutes=f.allowed_delay_minutes + f.cadence_minutes) + timedelta(
            hours=4
        )
        age = (clock - latest_seeded) if latest_seeded else None
        feeds.append(
            {
                "code": f.code,
                "name": f.name,
                "signal_class": f.signal_class.value,
                "cadence_minutes": f.cadence_minutes,
                "allowed_delay_minutes": f.allowed_delay_minutes,
                "location_level": f.location_level,
                "source": f.source.value,
                "enabled": f.enabled,
                "readings": count,
                "latest": latest_seeded.isoformat() if latest_seeded else None,
                "age_hours": round(age.total_seconds() / 3600, 1) if age is not None else None,
                "late": age is None or age > allowed,
                "live_latest": latest_live.isoformat() if latest_live else None,
                "live_age_hours": round((real_now - latest_live).total_seconds() / 3600, 1)
                if latest_live
                else None,
            }
        )
    status = session.get(Setting, "live_weather_status")
    return {"feeds": feeds, "live_weather": status.value if status else None}


class ConnectBody(BaseModel):
    name: str
    csv: str


def _proposal_out(pid: str, p: Proposal) -> dict[str, Any]:
    return {
        "id": pid,
        "name": p.name,
        "ai_available": p.ai_available,
        "columns": [
            {"column": c, "field": m.field, "free_text": m.free_text, "confidence": m.confidence}
            for c, m in p.columns.items()
        ],
        "preview": [
            {k: (None if p.columns[k].free_text else v) for k, v in row.items()}
            for row in p.rows[:5]
        ],
        "rows": len(p.rows),
    }


@router.post("/connect")
def connect(
    body: ConnectBody,
    session: SessionDep,
    user: Person = Depends(require_role("hse_head", "admin")),
) -> dict[str, Any]:
    if not body.name.strip() or not body.csv.strip():
        raise ApiError(422, "invalid_input", "Give the feed a name and a CSV file.")
    if len(body.csv) > 2_000_000:
        raise ApiError(422, "invalid_input", "The file is too large for this prototype (2 MB).")
    try:
        proposal = propose_mapping(session, body.name.strip(), body.csv)
    except ValueError as error:
        raise ApiError(422, "invalid_input", str(error)) from None
    pid = uuid.uuid4().hex[:12]
    session.add(
        Setting(
            key=f"feed_proposal_{pid}",
            value={
                "name": proposal.name,
                "csv": body.csv,
                "columns": {
                    c: {"field": m.field, "free_text": m.free_text, "confidence": m.confidence}
                    for c, m in proposal.columns.items()
                },
            },
        )
    )
    session.commit()
    return _proposal_out(pid, proposal)


class ConfirmBody(BaseModel):
    signal_class: str
    metric: str
    fields: dict[str, str] = {}


@router.post("/connect/{pid}/confirm", status_code=201)
def confirm(
    pid: str,
    body: ConfirmBody,
    session: SessionDep,
    user: Person = Depends(require_role("hse_head", "admin")),
) -> dict[str, Any]:
    stored = session.get(Setting, f"feed_proposal_{pid}")
    if stored is None:
        raise not_found("proposal")
    import csv
    import io

    data = stored.value
    reader = csv.DictReader(io.StringIO(data["csv"]))
    proposal = Proposal(
        name=data["name"],
        header=[h for h in (reader.fieldnames or []) if h],
        rows=[{k: v for k, v in r.items() if k is not None} for r in reader],
    )
    for col, m in data["columns"].items():
        field = body.fields.get(col, m["field"])
        proposal.columns[col] = ColumnMap(
            field="ignore" if m["free_text"] else field,
            free_text=m["free_text"],
            confidence=m["confidence"],
        )
    try:
        feed = confirm_mapping(session, proposal, body.signal_class, body.metric, user)
    except ValueError as error:
        raise ApiError(422, "invalid_input", str(error)) from None
    session.delete(stored)
    session.commit()
    return {"code": feed.code, "name": feed.name, "id": feed.id}


__all__ = ["router", "json"]
