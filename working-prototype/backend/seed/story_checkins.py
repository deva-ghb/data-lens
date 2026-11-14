"""The crews' check-ins for the story night, written ahead of the site clock.

Workers check in on their phones in the half hour before a shift. For the night of
29 July those check-ins lie after the scenario's clock, so the engine does not see
them until the clock reaches them: the evening run on 28 July scores without them,
and the shift-start re-score at 19:00 on 29 July has them. Arjun checks in on camera,
and Kiran Shrestha never does, so the re-score shows one missing check-in.

A separate random stream keeps every number the rest of the seed produced unchanged.
"""

from datetime import date, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assignment, CheckIn, Person, Shift
from app.models.roster import Feeling, ShiftKind
from seed.scenario import SEED

STORY_NIGHT = date(2026, 7, 29)
CHECKS_IN_ON_CAMERA = "arjun.thapa"
NEVER_CHECKS_IN = "kiran.shrestha"


def write_story_checkins(session: Session) -> None:
    rng = np.random.default_rng(SEED + 729)
    night = session.scalars(
        select(Shift).where(Shift.date == STORY_NIGHT, Shift.kind == ShiftKind.NIGHT)
    ).one()
    rows = session.execute(
        select(Person.id, Person.email)
        .join(Assignment, Assignment.person_id == Person.id)
        .where(Assignment.shift_id == night.id)
        .order_by(Person.id)
    ).all()
    skipped = {f"{CHECKS_IN_ON_CAMERA}@", f"{NEVER_CHECKS_IN}@"}
    assert sum(1 for _, email in rows if any(email.startswith(s) for s in skipped)) == 2
    for person_id, email in rows:
        if any(email.startswith(s) for s in skipped):
            continue
        r = rng.random()
        band = (
            "under_5" if r < 0.07 else "5_to_6" if r < 0.22 else "6_to_7" if r < 0.6 else "7_plus"
        )
        session.add(
            CheckIn(
                person_id=person_id,
                shift_id=night.id,
                at=night.start_at - timedelta(minutes=int(10 + rng.integers(0, 26))),
                sleep_hours_band=band,
                feeling=Feeling.TIRED if rng.random() < 0.1 else Feeling.GOOD,
                hydration_ok=bool(rng.random() > 0.05),
            )
        )
    session.flush()
