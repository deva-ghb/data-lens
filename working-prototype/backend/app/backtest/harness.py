"""The back-test harness: replay the scenario day by day and measure the detector.

Each day the detector sees only data up to the end of that day. Warnings in the same
district within three days of each other form one episode. An episode is true when it
starts between an injected event's first signal (less a day) and the harm it would
have led to, in the event's district; otherwise it is a false alarm.

Six measures, as the challenge asks: lead time, sensitivity, positive predictive value,
false alarms, data latency, and behaviour with feeds switched off. The action line is
swept from 1.2 to 2.0 and the most sensitive line that keeps every day inside the alert
budget is chosen.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.detector.detect import detect, evaluation_time
from app.detector.series import feed_index
from app.engine.budget import PLANNER_LIMIT
from app.models import Feed, Setting, Zone
from app.models.warnings import WarningLevel

REPLAY_START = date(2026, 5, 8)
REPLAY_END = date(2026, 7, 28)
EPISODE_GAP_DAYS = 3
SWEEP_LINES = [1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]


@dataclass
class Episode:
    district: str
    zones: list[str]
    first_day: date
    last_day: date
    peak_index: float
    event: str | None = None


@dataclass
class BacktestResult:
    action_line: float
    feeds_off: list[str]
    days: int
    lead_time_hours: dict[str, float | None]
    sensitivity: tuple[int, int]
    ppv: float
    false_alarms: int
    false_alarms_per_30d: float
    latency_by_feed: dict[str, float]
    budget_breaches: int
    episodes: list[Episode] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["sensitivity"] = list(self.sensitivity)
        for episode in data["episodes"]:
            episode["first_day"] = episode["first_day"].isoformat()
            episode["last_day"] = episode["last_day"].isoformat()
        return data


def _districts(session: Session) -> dict[str, str]:
    zones = {z.id: z for z in session.scalars(select(Zone))}
    out = {}
    for z in zones.values():
        out[z.name] = zones[z.parent_id].name if z.parent_id else z.name
    return out


def injected_events(session: Session) -> list[dict[str, Any]]:
    setting = session.get(Setting, "injected_events")
    return list(setting.value) if setting else []


def run_backtest(
    session: Session,
    action_line: float,
    feeds_off: frozenset[str] = frozenset(),
    start: date = REPLAY_START,
    end: date = REPLAY_END,
) -> BacktestResult:
    index = feed_index(session)
    district_of = _districts(session)
    episodes: list[Episode] = []
    open_by_district: dict[str, Episode] = {}
    new_per_day: dict[date, int] = {}
    day = start
    while day <= end:
        for signal in detect(session, day, action_line, feeds_off):
            if signal.level not in (WarningLevel.WARNING, WarningLevel.ALERT):
                continue
            zone = index.zone_name[signal.zone_id]
            district = district_of[zone]
            current = open_by_district.get(district)
            if current and (day - current.last_day).days <= EPISODE_GAP_DAYS:
                current.last_day = day
                current.peak_index = max(current.peak_index, signal.index)
                if zone not in current.zones:
                    current.zones.append(zone)
                continue
            episode = Episode(district, [zone], day, day, signal.index)
            episodes.append(episode)
            open_by_district[district] = episode
            new_per_day[day] = new_per_day.get(day, 0) + 1
        day += timedelta(days=1)

    events = injected_events(session)
    lead: dict[str, float | None] = {}
    for event in events:
        signal_start = datetime.fromisoformat(event["signal_start"])
        harm_at = datetime.fromisoformat(event["harm_at"])
        district = district_of[event["zone"]]
        matches = [
            e
            for e in episodes
            if e.district == district
            and signal_start - timedelta(days=1) <= evaluation_time(e.first_day) < harm_at
        ]
        if matches:
            first = min(matches, key=lambda e: e.first_day)
            for e in matches:
                e.event = event["code"]
            lead[event["code"]] = round(
                (harm_at - evaluation_time(first.first_day)).total_seconds() / 3600, 1
            )
        else:
            lead[event["code"]] = None

    found = sum(1 for v in lead.values() if v is not None)
    true_episodes = sum(1 for e in episodes if e.event)
    false_episodes = len(episodes) - true_episodes
    days = (end - start).days + 1
    feeds = session.scalars(select(Feed).order_by(Feed.code)).all()
    return BacktestResult(
        action_line=action_line,
        feeds_off=sorted(feeds_off),
        days=days,
        lead_time_hours=lead,
        sensitivity=(found, len(events)),
        ppv=round(true_episodes / len(episodes), 3) if episodes else 0.0,
        false_alarms=false_episodes,
        false_alarms_per_30d=round(false_episodes / days * 30, 2),
        latency_by_feed={f.code: round(f.allowed_delay_minutes / 60, 1) for f in feeds},
        budget_breaches=sum(1 for n in new_per_day.values() if n > PLANNER_LIMIT),
        episodes=episodes,
    )


def sweep(session: Session, lines: list[float] | None = None) -> list[BacktestResult]:
    results = [run_backtest(session, line) for line in (lines or SWEEP_LINES)]
    chosen = choose_action_line(results)
    store = next(r for r in results if r.action_line == chosen)
    _store(session, results[-1] if lines else store, results, chosen)
    return results


def choose_action_line(results: list[BacktestResult]) -> float:
    """The most sensitive line that keeps every day inside the alert budget; ties go to
    the line with the better positive predictive value, then the higher line."""
    inside = [r for r in results if r.budget_breaches == 0] or results
    best = max(inside, key=lambda r: (r.sensitivity[0], r.ppv, r.action_line))
    return best.action_line


def _store(
    session: Session, result: BacktestResult, results: list[BacktestResult], chosen: float
) -> None:
    value = result.as_json()
    value["chosen_action_line"] = chosen
    value["sweep"] = [
        {
            "action_line": r.action_line,
            "sensitivity": list(r.sensitivity),
            "ppv": r.ppv,
            "false_alarms_per_30d": r.false_alarms_per_30d,
            "budget_breaches": r.budget_breaches,
        }
        for r in results
    ]
    existing = session.get(Setting, "backtest_last")
    if existing is None:
        session.add(Setting(key="backtest_last", value=value))
    else:
        existing.value = value
    session.flush()
