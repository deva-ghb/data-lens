"""Daily series per feed, metric and zone, read from the ingested feed readings.

Each reading is placed on its local (UTC+4) day. Counts are summed per day; levels such
as PM10 are averaged. District zones see their own readings plus their blocks', so a
record with no block location counts toward the district and nothing else.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Feed, FeedReading, Zone
from app.models.feeds import FeedSource

LOCAL = timedelta(hours=4)


@dataclass(frozen=True)
class SeriesDef:
    feed: str
    metric: str
    level: bool = False  # a level (averaged), not a count (summed)


SERIES = [
    SeriesDef("CLINIC_VISITS", "heat_visits"),
    SeriesDef("CLINIC_VISITS", "respiratory_visits"),
    SeriesDef("CLINIC_VISITS", "gastro_visits"),
    SeriesDef("CLINIC_VISITS", "injury_visits"),
    SeriesDef("CLINIC_VISITS", "musculoskeletal_visits"),
    SeriesDef("SICKNESS_ABSENCE", "absent"),
    SeriesDef("SAFETY_REPORTS", "unsafe_reports"),
    SeriesDef("CHECKINS", "tired"),
    SeriesDef("CHECKINS", "short_sleep"),
    SeriesDef("CAMP_TICKETS", "tickets_opened"),
    SeriesDef("CAMP_TICKETS", "cooling_units_down", level=True),
    SeriesDef("AIR_QUALITY", "pm10", level=True),
]


def local_day(at: datetime) -> date:
    return (at + LOCAL).date()


class FeedIndex:
    """All detection series in memory, plus each feed's latest reading time."""

    def __init__(self, session: Session) -> None:
        self.feeds = {f.code: f for f in session.scalars(select(Feed))}
        zones = list(session.scalars(select(Zone)))
        self.zone_name = {z.id: z.name for z in zones}
        self.parent = {z.id: z.parent_id for z in zones}
        self.children: dict[int, list[int]] = defaultdict(list)
        for z in zones:
            if z.parent_id is not None:
                self.children[z.parent_id].append(z.id)
        wanted = {(s.feed, s.metric) for s in SERIES}
        feed_code = {f.id: f.code for f in self.feeds.values()}
        sums: dict[tuple[str, str, int | None], dict[date, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        counts: dict[tuple[str, str, int | None], dict[date, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.readings_at: dict[str, list[datetime]] = defaultdict(list)
        rows = session.execute(
            select(
                FeedReading.feed_id,
                FeedReading.zone_id,
                FeedReading.at,
                FeedReading.metric,
                FeedReading.value,
            ).where(FeedReading.source != FeedSource.LIVE)
        )
        for feed_id, zone_id, at, metric, value in rows:
            code = feed_code[feed_id]
            self.readings_at[code].append(at)
            if (code, metric) not in wanted:
                continue
            day = local_day(at)
            sums[(code, metric, zone_id)][day] += value
            counts[(code, metric, zone_id)][day] += 1
        for times in self.readings_at.values():
            times.sort()
        self.daily: dict[tuple[str, str, int | None], dict[date, float]] = {}
        levels = {(s.feed, s.metric) for s in SERIES if s.level}
        for key, by_day in sums.items():
            if (key[0], key[1]) in levels:
                self.daily[key] = {d: v / counts[key][d] for d, v in by_day.items()}
            else:
                self.daily[key] = dict(by_day)

    def value(self, series: SeriesDef, zone_id: int, day: date) -> float | None:
        """A zone's value for a day; districts add up their blocks (levels: average)."""
        own = self.daily.get((series.feed, series.metric, zone_id), {}).get(day)
        kids = [
            self.daily.get((series.feed, series.metric, c), {}).get(day)
            for c in self.children[zone_id]
        ]
        kids = [k for k in kids if k is not None]
        values = ([own] if own is not None else []) + kids
        if not values:
            return None
        return sum(values) / len(values) if series.level else sum(values)

    def zone_value(self, series: SeriesDef, zone_id: int, day: date) -> tuple[float | None, int]:
        """The value that applies to a zone: its own series, or its district's for
        district-wide feeds such as air quality. Returns (value, zone the value came from)."""
        value = self.value(series, zone_id, day)
        if value is not None:
            return value, zone_id
        parent = self.parent.get(zone_id)
        if parent is not None:
            parent_value = self.daily.get((series.feed, series.metric, parent), {}).get(day)
            if parent_value is not None:
                return parent_value, parent
        return None, zone_id

    def latest_before(self, feed: str, moment: datetime) -> datetime | None:
        times = self.readings_at.get(feed, [])
        lo, hi = 0, len(times)
        while lo < hi:
            mid = (lo + hi) // 2
            if times[mid] <= moment:
                lo = mid + 1
            else:
                hi = mid
        return times[lo - 1] if lo else None


def feed_index(session: Session) -> FeedIndex:
    key = ("feed_index",)
    if key not in session.info:
        session.info[key] = FeedIndex(session)
    return session.info[key]


def clear_feed_index(session: Session) -> None:
    session.info.pop(("feed_index",), None)
