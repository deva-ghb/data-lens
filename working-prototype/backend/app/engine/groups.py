"""Behavioural groups: who belongs where, and each group's unsafe rate against the site.

Membership is read from training, tenure and roster records as of a moment in time
(seed/catalog.py `classify_group`). Names, origin and language are never inputs.
A group's multiplier is its unsafe-act rate per 100 observation cards on grade 3 to 5
work in the last 12 months, divided by the site's rate. Groups under 20 people are not
assessed and carry a multiplier of 1.0.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.group_defs import GROUPS, classify_group
from app.models import (
    Absence,
    Activity,
    Assignment,
    Competency,
    Observation,
    Person,
    PersonCompetency,
    Role,
    Shift,
    TrainingRecord,
)
from app.models.records import ObservationKind
from app.models.roster import ShiftKind

MIN_GROUP_SIZE = 20
UNSAFE_KINDS = (ObservationKind.UNSAFE_ACT, ObservationKind.UNSAFE_BEHAVIOUR)


@dataclass(frozen=True)
class GroupRate:
    code: str
    name: str
    people: int
    cards: int
    unsafe: int
    unsafe_per_100_cards: float
    multiplier: float
    assessed: bool


def _months(start: date, end: date) -> float:
    return (end - start).days / 30.4


def _max_nights_in_row(night_dates: set[date], first: date, last: date) -> int:
    best = run = 0
    day = first
    while day <= last:
        run = run + 1 if day in night_dates else 0
        best = max(best, run)
        day += timedelta(days=1)
    return best


def memberships(session: Session, as_of: datetime) -> dict[int, str | None]:
    """Every worker's behavioural group as of a moment, from records in bulk."""
    cache_key = ("memberships", as_of)
    if cache_key in session.info:
        return session.info[cache_key]
    workers = session.execute(
        select(Person.id, Person.hire_date, Person.induction).where(Person.role == Role.WORKER)
    ).all()
    competencies: dict[int, set[str]] = defaultdict(set)
    for pid, code in session.execute(
        select(PersonCompetency.person_id, Competency.code).join(
            Competency, Competency.id == PersonCompetency.competency_id
        )
    ):
        competencies[pid].add(code)
    courses: dict[int, dict[str, date]] = defaultdict(dict)
    for pid, code, done in session.execute(
        select(TrainingRecord.person_id, TrainingRecord.course_code, TrainingRecord.completed_on)
    ):
        if done <= as_of.date() and done > courses[pid].get(code, date.min):
            courses[pid][code] = done
    window_start = as_of - timedelta(days=14)
    nights: dict[int, set[date]] = defaultdict(set)
    for pid, day in session.execute(
        select(Assignment.person_id, Shift.date)
        .join(Shift, Shift.id == Assignment.shift_id)
        .where(
            Shift.kind == ShiftKind.NIGHT, Shift.start_at >= window_start, Shift.start_at < as_of
        )
    ):
        nights[pid].add(day)
    # Nights worked, not just rostered.
    for pid, day in session.execute(
        select(Absence.person_id, Absence.date).where(
            Absence.date >= window_start.date(), Absence.date <= as_of.date()
        )
    ):
        nights[pid].discard(day)
    result: dict[int, str | None] = {}
    for pid, hire, induction in workers:
        history = {
            "tenure_months": _months(hire, as_of.date()),
            "induction": str(induction),
            "competencies": competencies[pid],
            "courses": set(courses[pid]),
            "months_since": {c: _months(d, as_of.date()) for c, d in courses[pid].items()},
            "nights_in_row_max_14d": _max_nights_in_row(
                nights[pid], window_start.date(), as_of.date()
            ),
        }
        result[pid] = classify_group(history)
    session.info[cache_key] = result
    return result


def group_rates(session: Session, as_of: datetime, cap: float = 1.6) -> dict[str, GroupRate]:
    cache_key = ("group_rates", as_of, cap)
    if cache_key in session.info:
        return session.info[cache_key]
    members = memberships(session, as_of)
    graded = set(session.scalars(select(Activity.id).where(Activity.grade >= 3)))
    cards: dict[str | None, int] = defaultdict(int)
    unsafe: dict[str | None, int] = defaultdict(int)
    for pid, activity_id, kind in session.execute(
        select(Observation.person_id, Observation.activity_id, Observation.kind).where(
            Observation.person_id.is_not(None),
            Observation.at >= as_of - timedelta(days=365),
            Observation.at < as_of,
        )
    ):
        if activity_id not in graded or pid not in members:
            continue
        group = members[pid]
        cards[group] += 1
        if kind in UNSAFE_KINDS:
            unsafe[group] += 1
    total_cards = sum(cards.values())
    site_rate = sum(unsafe.values()) / total_cards if total_cards else 0.0
    sizes: dict[str | None, int] = defaultdict(int)
    for group in members.values():
        sizes[group] += 1
    rates: dict[str, GroupRate] = {}
    for g in GROUPS:
        rate = unsafe[g.code] / cards[g.code] if cards[g.code] else 0.0
        assessed = sizes[g.code] >= MIN_GROUP_SIZE and cards[g.code] > 0 and site_rate > 0
        multiplier = min(rate / site_rate, cap) if assessed else 1.0
        rates[g.code] = GroupRate(
            code=g.code,
            name=g.name,
            people=sizes[g.code],
            cards=cards[g.code],
            unsafe=unsafe[g.code],
            unsafe_per_100_cards=round(rate * 100, 1),
            multiplier=round(multiplier, 3),
            assessed=assessed,
        )
    session.info[cache_key] = rates
    return rates
