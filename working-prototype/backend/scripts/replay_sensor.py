"""Replay a berth's deck WBGT into the running app, the way a sensor gateway would.

Usage:
  uv run python scripts/replay_sensor.py --from 2026-07-29T15:00 --to 2026-07-29T16:30 \
      [--berth "Berth 2"] [--step 10] [--pause 1.0] [--base-url http://localhost:8000]

Each reading is posted to /api/ingest/sensor with the gateway token. The site clock is
moved to each reading's time through the admin API, so the screens follow along.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.feeds.ingest import gateway_token  # noqa: E402
from seed.catalog import KEY_USERS, PASSWORD  # noqa: E402
from seed.deck_replay import deck_series  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="start", required=True)
    parser.add_argument("--to", dest="end", required=True)
    parser.add_argument("--berth", default="Berth 2")
    parser.add_argument("--step", type=int, default=10)
    parser.add_argument("--pause", type=float, default=1.0, help="seconds between readings")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    admin = next(u for u in KEY_USERS if u.role == "admin")
    with httpx.Client(base_url=args.base_url, timeout=30) as http:
        login = http.post("/api/auth/login", json={"email": admin.email, "password": PASSWORD})
        login.raise_for_status()
        token = gateway_token()
        for at, value in deck_series(
            args.berth,
            datetime.fromisoformat(args.start),
            datetime.fromisoformat(args.end),
            args.step,
        ):
            http.put("/api/admin/clock", json={"now": at.isoformat()}).raise_for_status()
            body = {
                "sensor_id": f"deck-{args.berth.lower().replace(' ', '')}-01",
                "zone_code": args.berth,
                "at": at.isoformat(),
                "metric": "wbgt",
                "value": value,
            }
            http.post(
                "/api/ingest/sensor", json=body, headers={"X-Gateway-Token": token}
            ).raise_for_status()
            print(f"{at:%H:%M} UTC  {args.berth}  deck WBGT {value:.1f} C")
            time.sleep(args.pause)


if __name__ == "__main__":
    main()
