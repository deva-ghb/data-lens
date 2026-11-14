"""Deck WBGT as a berth gateway would send it, from the real archived weather.

Readings every few minutes are interpolated from the hourly weather, plus the berth's
steel-deck offset and a small, repeatable wobble.
"""

from datetime import datetime, timedelta
from math import sin

from app.feeds.wbgt import estimate_wbgt
from seed.signals import load_archive

BERTH_OFFSET = {"Berth 1": 0.4, "Berth 2": 0.7, "Berth 3": 0.5, "Berth 4": 0.3}


def deck_series(
    berth: str, start: datetime, end: datetime, step_minutes: int = 10
) -> list[tuple[datetime, float]]:
    archive = load_archive()
    out = []
    t = start
    while t <= end:
        hour = t.replace(minute=0, second=0)
        a, b = archive[hour], archive.get(hour + timedelta(hours=1), archive[hour])
        f = t.minute / 60
        temp = a["temp_c"] + (b["temp_c"] - a["temp_c"]) * f
        rh = a["rh_pct"] + (b["rh_pct"] - a["rh_pct"]) * f
        sun = a["radiation_wm2"] + (b["radiation_wm2"] - a["radiation_wm2"]) * f
        wobble = 0.15 * sin(t.minute / 7)
        out.append((t, round(estimate_wbgt(temp, rh, sun) + BERTH_OFFSET[berth] + wobble, 2)))
        t += timedelta(minutes=step_minutes)
    return out
