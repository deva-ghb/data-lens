"""On-site sensors: deck WBGT readings arriving from the berth gateways.

When a live permit's berth reads over 32 C WBGT for 30 minutes, the permit log records
it and a work-rest change waits for the foreman to confirm on their phone. It is raised
once per hot spell, not on every reading.
"""

import hashlib
import hmac
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Feed, FeedReading, Permit, PermitEvent, Zone
from app.models.feeds import FeedSource
from app.models.permits import PermitStatus

LIMIT_C = 32.0
SUSTAINED = timedelta(minutes=30)


class UnknownZone(LookupError):
    pass


def gateway_token() -> str:
    """The shared token the berth gateways send; derived from the app secret."""
    return hmac.new(settings.jwt_secret.encode(), b"sensor-gateway", hashlib.sha256).hexdigest()[
        :32
    ]


def ingest_sensor_reading(
    session: Session, sensor_id: str, zone_code: str, at: datetime, metric: str, value: float
) -> FeedReading:
    zone = session.scalars(select(Zone).where(Zone.name == zone_code)).first()
    if zone is None:
        raise UnknownZone(zone_code)
    feed_id = session.scalars(select(Feed.id).where(Feed.code == "WEATHER")).one()
    reading = FeedReading(
        feed_id=feed_id,
        zone_id=zone.id,
        at=at,
        metric="deck_wbgt" if metric == "wbgt" else metric,
        value=value,
        source=FeedSource.SEEDED,
    )
    session.add(reading)
    session.flush()
    if reading.metric == "deck_wbgt":
        _check_limit(session, zone, at, feed_id)
    return reading


def _check_limit(session: Session, zone: Zone, at: datetime, feed_id: int) -> None:
    window = session.execute(
        select(FeedReading.at, FeedReading.value)
        .where(
            FeedReading.feed_id == feed_id,
            FeedReading.zone_id == zone.id,
            FeedReading.metric == "deck_wbgt",
            FeedReading.at >= at - SUSTAINED,
            FeedReading.at <= at,
        )
        .order_by(FeedReading.at)
    ).all()
    if not window or at - window[0].at < SUSTAINED or any(v <= LIMIT_C for _, v in window):
        return
    permits = session.scalars(
        select(Permit).where(Permit.zone_id == zone.id, Permit.status == PermitStatus.LIVE)
    ).all()
    for permit in permits:
        recent = session.scalars(
            select(PermitEvent).where(
                PermitEvent.permit_id == permit.id,
                PermitEvent.kind == "wbgt_limit",
                PermitEvent.at >= at - timedelta(hours=2),
            )
        ).first()
        if recent is not None:
            continue
        peak = max(v for _, v in window)
        session.add(
            PermitEvent(
                permit_id=permit.id,
                at=at,
                kind="wbgt_limit",
                text=(
                    f"Deck WBGT over {LIMIT_C:.0f} C for 30 minutes at {zone.name} "
                    f"(peak {peak:.1f} C)."
                ),
                actor_id=None,
            )
        )
        session.add(
            PermitEvent(
                permit_id=permit.id,
                at=at,
                kind="work_rest_change_pending",
                text=(
                    "Work-rest cycle to 30 minutes on, 30 minutes off in the shade. "
                    "Waiting for the foreman."
                ),
                actor_id=None,
            )
        )
    session.flush()
