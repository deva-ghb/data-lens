"""Fixed dates and clock settings for the synthetic scenario.

All stored datetimes are naive UTC. The site is UTC+4.
Day shifts run 07:00 to 19:00 local (03:00 to 15:00 UTC); night shifts run
19:00 to 07:00 local (15:00 to 03:00 UTC the next day).
"""

from datetime import date, datetime, timedelta

from app.models.roster import ShiftKind

SEED = 20260729
LOCAL_OFFSET = timedelta(hours=4)

ROSTER_START = date(2026, 5, 1)
ROSTER_END = date(2026, 7, 29)  # inclusive: the night of 29 July is the story's shift
HISTORY_START = datetime(2025, 8, 1)  # observation cards and reports go back 12 months
CLOCK = datetime(2026, 7, 28, 14, 0)  # 18:00 local on 28 July, the evening before
STORY_DATE = date(2026, 7, 29)


def shift_window(day: date, kind: ShiftKind) -> tuple[datetime, datetime]:
    start_hour = 3 if kind == ShiftKind.DAY else 15
    start = datetime(day.year, day.month, day.day, start_hour)
    return start, start + timedelta(hours=12)


def roster_days() -> list[date]:
    days = (ROSTER_END - ROSTER_START).days + 1
    return [ROSTER_START + timedelta(days=i) for i in range(days)]


def local(dt: datetime) -> datetime:
    return dt + LOCAL_OFFSET
