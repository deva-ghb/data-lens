"""The live weather feed: the real Abu Dhabi forecast from Open-Meteo, pulled hourly.

Readings are stored in the WEATHER feed marked "live", next to the seeded scenario
weather. A failed pull stores nothing, keeps what was there, and records the failure, so
the feed shows as late wherever it is used. Nothing is filled in silently.
"""

from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Feed, FeedReading, Setting
from app.models.feeds import FeedSource

URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE, LONGITUDE = 24.45, 54.38
STATUS_KEY = "live_weather_status"
METRICS = {
    "temperature_2m": "temp_c",
    "relative_humidity_2m": "rh_pct",
    "wind_speed_10m": "wind_ms",
    "shortwave_radiation": "radiation_wm2",
}
_transport: httpx.BaseTransport | None = None


def set_transport(transport: httpx.BaseTransport | None) -> None:
    global _transport
    _transport = transport


def _status(session: Session, **values: object) -> None:
    row = session.get(Setting, STATUS_KEY)
    current = dict(row.value) if row else {}
    current.update(values)
    if row is None:
        session.add(Setting(key=STATUS_KEY, value=current))
    else:
        row.value = current
    session.flush()


def pull_live_forecast(session: Session) -> int:
    """Store the next 48 hours of forecast. Returns how many readings were added."""
    now = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": ",".join(METRICS),
        "wind_speed_unit": "ms",
        "timezone": "UTC",
        "forecast_days": 2,
    }
    try:
        with httpx.Client(timeout=20, transport=_transport) as http:
            response = http.get(URL, params=params)
        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"status {response.status_code}", request=response.request, response=response
            )
        hourly = response.json()["hourly"]
    except (httpx.HTTPError, KeyError, ValueError) as error:
        _status(session, ok=False, error=str(error)[:200], last_attempt=now.isoformat())
        return 0
    feed_id = session.scalars(select(Feed.id).where(Feed.code == "WEATHER")).one()
    times = [datetime.fromisoformat(t) for t in hourly["time"]]
    # A newer forecast replaces the hours it covers.
    session.execute(
        FeedReading.__table__.delete().where(
            FeedReading.feed_id == feed_id,
            FeedReading.source == FeedSource.LIVE,
            FeedReading.at.in_(times),
        )
    )
    added = 0
    for i, at in enumerate(times):
        for source_name, metric in METRICS.items():
            value = hourly[source_name][i]
            if value is None:
                continue
            session.add(
                FeedReading(
                    feed_id=feed_id,
                    zone_id=None,
                    at=at,
                    metric=metric,
                    value=float(value),
                    source=FeedSource.LIVE,
                )
            )
            added += 1
    session.flush()
    _status(
        session,
        ok=True,
        error=None,
        last_success=now.isoformat(),
        last_attempt=now.isoformat(),
        hours=len(times),
    )
    return added
