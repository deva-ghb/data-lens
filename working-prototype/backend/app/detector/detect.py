"""The early warning detector: deviation from each zone's own baseline, per day.

For each zone and each series, the last three days are compared with the 28 days before
them. A series is up when it runs at least 1.5 times its baseline and, for counts, is at
least two events above expected and a rise that large would happen by chance on fewer
than 2.5 percent of days (a one-sided Poisson test).
The level then follows the rules in the concept doc:

- Watch: one signal class is up, or the index reaches 0.8 times the action line.
- Warning: two or more classes agree in the same zone and period, and the index (the
  average ratio of the up series) reaches the action line.
- Alert: three or more classes and an index of 1.5 times the action line.
- With fewer than two classes live, nothing goes above Watch.
- Without the clinic or weather feed, the level drops one step, and the feed is named.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from math import exp

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.detector.series import SERIES, FeedIndex, SeriesDef, feed_index
from app.models import WarningRecord
from app.models.warnings import WarningLevel, WarningStatus

WINDOW_DAYS = 3
BASELINE_DAYS = 28
UP_RATIO = 1.5
MIN_EXCESS = 2.0
SMOOTHING = 0.5
MAX_CHANCE = 0.025  # a count is up only if a rise this large happens by chance under 2.5% of days
DROP_IF_MISSING = ("CLINIC_VISITS", "WEATHER")
LEVELS = [None, WarningLevel.WATCH, WarningLevel.WARNING, WarningLevel.ALERT]
DETECTION_FEEDS = sorted({s.feed for s in SERIES} | {"WEATHER"})


@dataclass(frozen=True)
class SeriesResult:
    feed: str
    metric: str
    zone_id: int
    period_start: date
    period_end: date
    observed: float
    expected: float
    ratio: float
    up: bool


@dataclass
class ZoneEvaluation:
    zone_id: int
    day: date
    level: WarningLevel | None
    index: float
    classes_agreeing: set[str]
    contributions: list[SeriesResult]
    all_series: list[SeriesResult]
    late_feeds: list[str] = field(default_factory=list)


Signal = ZoneEvaluation


def evaluation_time(day: date) -> datetime:
    """The detector runs at local midnight at the end of `day` (20:00 UTC)."""
    return datetime(day.year, day.month, day.day, 20)


def _excluded_days(session: Session, zone_id: int) -> set[date]:
    days: set[date] = set()
    for opened, closed in session.execute(
        select(WarningRecord.opened_at, WarningRecord.closed_at).where(
            WarningRecord.zone_id == zone_id, WarningRecord.status == WarningStatus.OPEN
        )
    ):
        start = (opened + timedelta(hours=4)).date()
        end = (closed + timedelta(hours=4)).date() if closed else start + timedelta(days=60)
        day = start
        while day <= end:
            days.add(day)
            day += timedelta(days=1)
    return days


def poisson_tail(observed: float, expected: float) -> float:
    """Chance of seeing at least `observed` events when `expected` are usual."""
    k = int(round(observed))
    if k <= 0:
        return 1.0
    mu = max(expected, 0.05)
    term = total = exp(-mu)
    for i in range(1, k):
        term *= mu / i
        total += term
    return max(1.0 - total, 0.0)


def _series(
    index: FeedIndex, s: SeriesDef, zone_id: int, day: date, excluded: set[date]
) -> SeriesResult | None:
    window = [day - timedelta(days=i) for i in range(WINDOW_DAYS)]
    base_days = [
        day - timedelta(days=WINDOW_DAYS + i)
        for i in range(BASELINE_DAYS)
        if day - timedelta(days=WINDOW_DAYS + i) not in excluded
    ]
    win_values = [index.zone_value(s, zone_id, d) for d in window]
    observed_values = [v for v, _ in win_values if v is not None]
    if not observed_values:
        return None
    source_zone = win_values[0][1]
    base_values = [
        v for v, _ in (index.zone_value(s, zone_id, d) for d in base_days) if v is not None
    ]
    if len(base_values) < 7:
        return None
    w_mean = sum(observed_values) / len(observed_values)
    b_mean = sum(base_values) / len(base_values)
    if s.level:
        ratio = w_mean / b_mean if b_mean > 0 else 1.0
        if s.metric == "cooling_units_down":
            ratio = (w_mean + SMOOTHING) / (b_mean + SMOOTHING)
            up = ratio >= UP_RATIO and (w_mean - b_mean) >= MIN_EXCESS
        else:
            up = ratio >= UP_RATIO
    else:
        ratio = (w_mean + SMOOTHING) / (b_mean + SMOOTHING)
        observed_total = w_mean * len(observed_values)
        expected_total = b_mean * len(observed_values)
        up = (
            ratio >= UP_RATIO
            and observed_total - expected_total >= MIN_EXCESS
            and poisson_tail(observed_total, expected_total) < MAX_CHANCE
        )
    return SeriesResult(
        feed=s.feed,
        metric=s.metric,
        zone_id=source_zone,
        period_start=window[-1],
        period_end=day,
        observed=round(sum(observed_values), 2) if not s.level else round(w_mean, 2),
        expected=round(b_mean * len(observed_values), 2) if not s.level else round(b_mean, 2),
        ratio=round(ratio, 2),
        up=up,
    )


def _late_feeds(index: FeedIndex, day: date, feeds_off: frozenset[str]) -> list[str]:
    moment = evaluation_time(day)
    late = []
    for code in DETECTION_FEEDS:
        feed = index.feeds.get(code)
        if feed is None:
            continue
        latest = index.latest_before(code, moment)
        allowed = timedelta(minutes=feed.allowed_delay_minutes + feed.cadence_minutes) + timedelta(
            hours=4
        )
        if code in feeds_off or not feed.enabled or latest is None or moment - latest > allowed:
            late.append(code)
    return late


def evaluate_zone(
    session: Session,
    zone_id: int,
    day: date,
    action_line: float = UP_RATIO,
    feeds_off: frozenset[str] = frozenset(),
    index: FeedIndex | None = None,
) -> ZoneEvaluation:
    index = index or feed_index(session)
    late_codes = _late_feeds(index, day, feeds_off)
    excluded = _excluded_days(session, zone_id)
    results = []
    for s in SERIES:
        if s.feed in late_codes:
            continue
        result = _series(index, s, zone_id, day, excluded)
        if result is not None:
            results.append(result)
    up = [r for r in results if r.up]
    classes = {index.feeds[r.feed].signal_class.value for r in up}
    ratio_index = round(sum(r.ratio for r in up) / len(up), 2) if up else 1.0

    step = 0
    if len(classes) >= 3 and ratio_index >= 1.5 * action_line:
        step = 3
    elif len(classes) >= 2 and ratio_index >= action_line:
        step = 2
    elif classes or ratio_index >= 0.8 * action_line:
        step = 1 if up else 0
    if any(code in late_codes for code in DROP_IF_MISSING):
        step = max(step - 1, 0) if step >= 2 else step
    live_classes = {
        index.feeds[code].signal_class.value
        for code in DETECTION_FEEDS
        if code in index.feeds and code not in late_codes
    }
    if len(live_classes) < 2:
        step = min(step, 1)
    return ZoneEvaluation(
        zone_id=zone_id,
        day=day,
        level=LEVELS[step],
        index=ratio_index,
        classes_agreeing=classes,
        contributions=sorted(up, key=lambda r: r.ratio, reverse=True),
        all_series=results,
        late_feeds=[index.feeds[c].name for c in late_codes if c in index.feeds],
    )


def detect(
    session: Session,
    day: date,
    action_line: float = UP_RATIO,
    feeds_off: frozenset[str] = frozenset(),
) -> list[ZoneEvaluation]:
    index = feed_index(session)
    signals = []
    for zone_id in sorted(index.zone_name):
        evaluation = evaluate_zone(session, zone_id, day, action_line, feeds_off, index)
        if evaluation.level is not None:
            signals.append(evaluation)
    return signals
