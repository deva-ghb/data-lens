"""Pull the live forecast once an hour while the app runs (off when DATALENS_LIVE_WEATHER=0)."""

import os
import threading

from sqlalchemy.orm import Session

from app import db
from app.feeds.weather_live import pull_live_forecast

INTERVAL_SECONDS = 3600
_stop = threading.Event()


def _loop() -> None:
    while not _stop.is_set():
        try:
            with Session(db.engine) as session:
                pull_live_forecast(session)
                session.commit()
        except Exception:  # noqa: BLE001 - a failed pull must never stop the app
            pass
        _stop.wait(INTERVAL_SECONDS)


def start() -> None:
    if os.environ.get("DATALENS_LIVE_WEATHER", "1") == "0":
        return
    threading.Thread(target=_loop, name="live-weather", daemon=True).start()


def stop() -> None:
    _stop.set()
