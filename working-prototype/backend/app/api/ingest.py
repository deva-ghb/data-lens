"""Sensor gateway endpoint."""

import hmac
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import db
from app.errors import ApiError
from app.feeds.ingest import UnknownZone, gateway_token, ingest_sensor_reading

router = APIRouter(prefix="/ingest", tags=["ingest"])


class SensorReading(BaseModel):
    sensor_id: str
    zone_code: str
    at: datetime
    metric: str
    value: float


@router.post("/sensor", status_code=201)
def sensor(
    reading: SensorReading,
    session: Annotated[Session, Depends(db.get_session)],
    x_gateway_token: Annotated[str | None, Header()] = None,
) -> dict[str, int]:
    if not x_gateway_token or not hmac.compare_digest(x_gateway_token, gateway_token()):
        raise ApiError(401, "unauthorized", "This gateway is not recognised.")
    try:
        row = ingest_sensor_reading(
            session, reading.sensor_id, reading.zone_code, reading.at, reading.metric, reading.value
        )
    except UnknownZone:
        raise ApiError(404, "not_found", "That zone does not exist.") from None
    session.commit()
    return {"id": row.id}
