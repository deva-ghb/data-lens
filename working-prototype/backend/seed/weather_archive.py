"""Fetch real hourly weather for Abu Dhabi, 1 May to 29 July 2025, once.

Run manually: `uv run python -m seed.weather_archive`. The output is committed as
seed/data/abu_dhabi_2025_hourly.json and replayed onto 2026 dates by the generator,
so the scenario's summer is a real Gulf summer rather than an invented one.
Source: the Open-Meteo historical weather archive (free, no key).
"""

import json
from pathlib import Path

import httpx

LATITUDE = 24.45
LONGITUDE = 54.38
OUT = Path(__file__).resolve().parent / "data" / "abu_dhabi_2025_hourly.json"
URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch() -> dict[str, list]:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": "2025-05-01",
        "end_date": "2025-07-31",
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation",
        "wind_speed_unit": "ms",
        "timezone": "UTC",
    }
    response = httpx.get(URL, params=params, timeout=60)
    response.raise_for_status()
    hourly = response.json()["hourly"]
    return {
        "time": hourly["time"],
        "temp_c": hourly["temperature_2m"],
        "rh_pct": hourly["relative_humidity_2m"],
        "wind_ms": hourly["wind_speed_10m"],
        "radiation_wm2": hourly["shortwave_radiation"],
    }


if __name__ == "__main__":
    data = fetch()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"source": URL, "latitude": LATITUDE, "longitude": LONGITUDE, **data})
    )
    print(f"wrote {len(data['time'])} hours to {OUT}")
