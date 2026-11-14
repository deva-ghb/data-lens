"""The site clock: every time-based rule in the app reads the time from here.

The clock is a single database row. It stays where it is until the admin moves it
or the demo replay advances it, so the scenario is repeatable.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import audit
from app.models import Person, Shift, SiteClock


def site_now(session: Session) -> datetime:
    """The site's current time (naive UTC). Falls back to real time if the clock is unset."""
    clock = session.get(SiteClock, 1)
    if clock is None:
        return datetime.now(UTC).replace(tzinfo=None)
    return clock.now


def set_site_now(session: Session, at: datetime, actor: Person | None) -> None:
    """Move the site clock and record who moved it."""
    clock = session.get(SiteClock, 1)
    previous = clock.now if clock else None
    if clock is None:
        session.add(SiteClock(id=1, now=at))
    else:
        clock.now = at
    session.flush()
    audit(
        session,
        actor,
        "site_clock_set",
        "site_clock",
        "1",
        evidence={
            "from": previous.isoformat() if previous else None,
            "to": at.isoformat(),
        },
    )


def current_shift(session: Session) -> Shift:
    """The shift running at the site time (start inclusive, end exclusive)."""
    now = site_now(session)
    shift = session.scalar(
        select(Shift).where(Shift.start_at <= now, Shift.end_at > now).order_by(Shift.start_at)
    )
    if shift is None:
        raise LookupError("No shift covers the current site time.")
    return shift
