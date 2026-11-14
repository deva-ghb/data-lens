from datetime import datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.feeds import weather_live
from app.models import Feed, FeedReading, Setting
from app.models.feeds import FeedSource

FORECAST = {
    "hourly": {
        "time": ["2026-11-15T08:00", "2026-11-15T09:00"],
        "temperature_2m": [31.0, 32.5],
        "relative_humidity_2m": [55, 50],
        "wind_speed_10m": [3.1, 3.4],
        "shortwave_radiation": [610.0, 700.0],
    }
}


def _live_rows(session: Session) -> int:
    feed = session.scalars(select(Feed.id).where(Feed.code == "WEATHER")).one()
    return (
        session.scalar(
            select(func.count())
            .select_from(FeedReading)
            .where(FeedReading.feed_id == feed, FeedReading.source == FeedSource.LIVE)
        )
        or 0
    )


def test_pull_stores_live_readings(scenario: Session) -> None:
    weather_live.set_transport(httpx.MockTransport(lambda r: httpx.Response(200, json=FORECAST)))
    try:
        assert weather_live.pull_live_forecast(scenario) == 8
        assert _live_rows(scenario) == 8
        again = weather_live.pull_live_forecast(scenario)
        assert again == 8  # a newer forecast replaces the same hours
        assert _live_rows(scenario) == 8  # never stored twice
    finally:
        weather_live.set_transport(None)
    status = scenario.get_one(Setting, "live_weather_status").value
    assert status["ok"] is True and status["hours"] == 2


def test_failed_pull_marks_feed_late_and_keeps_old_rows(scenario: Session) -> None:
    weather_live.set_transport(httpx.MockTransport(lambda r: httpx.Response(200, json=FORECAST)))
    weather_live.pull_live_forecast(scenario)
    weather_live.set_transport(httpx.MockTransport(lambda r: httpx.Response(503)))
    try:
        assert weather_live.pull_live_forecast(scenario) == 0
    finally:
        weather_live.set_transport(None)
    assert _live_rows(scenario) == 8
    status = scenario.get_one(Setting, "live_weather_status").value
    assert status["ok"] is False and "503" in status["error"]
    assert datetime.fromisoformat(status["last_success"]) is not None
