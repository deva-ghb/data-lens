"""The synthetic workforce: 400 workers in crews, each with training, tenure and a camp block.

Behavioural groups are not stored. They emerge from the records written here
(induction, refreshers, tenure) and from the roster patterns in seed/history.py.
The cohort labels below only steer the generator; they are never saved.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from seed.catalog import KEY_USERS
from seed.names import DISPLAY_LANGUAGES, REGION_WEIGHTS, REGIONS
from seed.scenario import ROSTER_START, STORY_DATE

PATTERN_A = "DDDONNNO"  # at most three nights in a row
PATTERN_B = "DDONNNNO"  # four nights in a row: the extended night rotation


@dataclass
class CrewDef:
    name: str
    activity: str
    zone: str
    pattern: str
    phase: int
    alt_activity: str | None = None  # occasional other duty in the same competency


@dataclass
class WorkerSpec:
    first_name: str
    last_name: str
    employer: str
    cohort: str
    crew: str
    competencies: list[str]
    induction: str
    hire_date: date
    arrival_date: date
    camp: str | None
    display_language: str
    courses: dict[str, date] = field(default_factory=dict)
    key: str | None = None  # set for the named story worker

    @property
    def email_local(self) -> str:
        return f"{self.first_name}.{self.last_name}".lower()


def _phase_for(day: date, index: int, pattern: str) -> int:
    offset = (day - ROSTER_START).days
    return (index - offset) % len(pattern)


DECK_BERTHS = [1, 2, 2, 3, 4, 1, 3, 4, 2, 1]


def build_crews(rng: np.random.Generator) -> list[CrewDef]:
    crews: list[CrewDef] = []
    for k in range(1, 11):
        pattern = PATTERN_B if k in (7, 8) else PATTERN_A
        if k == 3:
            # The story gang: nights on 27, 28 and 29 July (pattern positions 4, 5, 6).
            phase = _phase_for(STORY_DATE, 6, PATTERN_A)
        else:
            phase = int(rng.integers(0, 8))
        crews.append(
            CrewDef(
                f"Deck Gang {k}",
                "LASH_DECK",
                f"Berth {DECK_BERTHS[k - 1]}",
                pattern,
                phase,
                alt_activity="TWIST_GROUND",
            )
        )
    for k in range(1, 4):
        crews.append(
            CrewDef(
                f"Mooring Gang {k}", "MOORING", f"Berth {k}", PATTERN_A, int(rng.integers(0, 8))
            )
        )
    for k in range(1, 11):
        activity = "REACH_STACKER" if k in (2, 5, 8) else "TT_DRIVING"
        crews.append(
            CrewDef(
                f"Yard Gang {k}",
                activity,
                f"Yard Block {(k - 1) % 6 + 1}",
                PATTERN_A,
                int(rng.integers(0, 8)),
            )
        )
    others = [
        ("QC Crew 1", "QC_OPS", "Berth 1"),
        ("QC Crew 2", "QC_OPS", "Berth 2"),
        ("Hold Crew", "HOLD_CONFINED", "Berth 2"),
        ("Hot Work Crew", "HOT_WORK", "Workshop Area"),
        ("Ground Gang 1", "TWIST_GROUND", "Berth 1"),
        ("Ground Gang 2", "TWIST_GROUND", "Berth 2"),
        ("Reefer Team 1", "REEFER", "Yard Block 5"),
        ("Reefer Team 2", "REEFER", "Yard Block 6"),
        ("Workshop Team", "WORKSHOP_MECH", "Workshop Area"),
        ("Inspection Team 1", "CONTAINER_INSPECT", "Yard Block 3"),
        ("Inspection Team 2", "CONTAINER_INSPECT", "Yard Block 1"),
        ("Housekeeping Crew", "YARD_HOUSEKEEPING", "Yard Block 6"),
        ("Gate Team", "GATE_CLERK", "Gate Complex"),
    ]
    for name, activity, zone in others:
        crews.append(CrewDef(name, activity, zone, PATTERN_A, int(rng.integers(0, 8))))
    return crews


# (crew name or prefix, cohort, count, employer split)
COMPETENCY_FOR = {
    "LASH_DECK": ["LASHING"],
    "MOORING": ["MOORING"],
    "TT_DRIVING": ["TT_DRIVER"],
    "REACH_STACKER": ["REACH_STACKER", "TT_DRIVER"],
    "QC_OPS": ["QC_OPERATOR"],
    "HOLD_CONFINED": ["CONFINED_SPACE"],
    "HOT_WORK": ["HOT_WORK"],
    "TWIST_GROUND": ["LASHING", "GROUND_OPS"],
    "REEFER": ["REEFER"],
    "WORKSHOP_MECH": ["MECHANIC"],
    "CONTAINER_INSPECT": ["INSPECTION"],
    "YARD_HOUSEKEEPING": ["GROUND_OPS"],
    "GATE_CLERK": ["GATE"],
}

SCENARIO_DAY = STORY_DATE


def _months_ago(months: float) -> date:
    return SCENARIO_DAY - timedelta(days=int(months * 30.4))


class _Namer:
    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.used: set[str] = {u.email.split("@")[0] for u in KEY_USERS}

    def next(self) -> tuple[str, str]:
        regions = list(REGION_WEIGHTS)
        weights = [REGION_WEIGHTS[r] for r in regions]
        while True:
            region = regions[int(self.rng.choice(len(regions), p=weights))]
            firsts, lasts = REGIONS[region]
            first = firsts[int(self.rng.integers(0, len(firsts)))]
            last = lasts[int(self.rng.integers(0, len(lasts)))]
            local = f"{first}.{last}".lower()
            if local not in self.used:
                self.used.add(local)
                return first, last


def _cohort_record(cohort: str, rng: np.random.Generator) -> tuple[date, str, dict[str, date]]:
    """Hire date, induction pathway and completed courses for a cohort."""
    r = rng.random
    if cohort == "exp_inhouse":
        hire = _months_ago(26 + r() * 90)
        return hire, "site", {"HEIGHT_REFRESHER": _months_ago(1 + r() * 10)}
    if cohort == "exp_nights":
        hire = _months_ago(26 + r() * 90)
        return hire, "site", {"HEIGHT_REFRESHER": _months_ago(2 + r() * 9)}
    if cohort == "new_contractor":
        return _months_ago(1.2 + r() * 4.5), "contractor", {}
    if cohort == "recent_arrival":
        return STORY_DATE - timedelta(days=6), "contractor", {}
    if cohort == "mid_lasher":
        hire = _months_ago(7 + r() * 15)
        courses = {"HEIGHT_REFRESHER": _months_ago(13 + r() * 6)} if r() < 0.5 else {}
        return hire, ("site" if r() < 0.4 else "contractor"), courses
    if cohort == "driver_refreshed":
        hire = _months_ago(8 + r() * 80)
        return hire, "site", {"DRIVING_REFRESHER": _months_ago(0.5 + r() * 5)}
    if cohort == "driver_overdue":
        hire = _months_ago(26 + r() * 80)
        return hire, "site", {"DRIVING_REFRESHER": _months_ago(19 + r() * 10)}
    if cohort == "driver_mid":
        hire = _months_ago(14 + r() * 60)
        return hire, "site", {"DRIVING_REFRESHER": _months_ago(7.5 + r() * 9.5)}
    hire = _months_ago(7 + r() * 97)  # nobody outside the story cohorts is a new arrival
    return hire, ("site" if r() < 0.6 else "contractor"), {}


def _employers(split: dict[str, int], rng: np.random.Generator) -> list[str]:
    names = [name for name, n in split.items() for _ in range(n)]
    rng.shuffle(names)
    return names


MIRSAL, SAHEL, BAYAN = "Mirsal Terminals", "Sahel Marine Services", "Bayan Manpower Contracting"
CAMPS = ["Camp Block A", "Camp Block B", "Camp Block C", "Camp Block D", "Camp Block E"]


def build_workers(rng: np.random.Generator, crews: list[CrewDef]) -> list[WorkerSpec]:
    namer = _Namer(rng)
    crew_by_name = {c.name: c for c in crews}
    slots: list[tuple[str, str, str]] = []  # (crew, cohort, employer)

    # Deck Gang 3, the story gang: Arjun, two arrivals from 23 July, two more new
    # contractors, four experienced in-house lashers and three mid-tenure lashers.
    gang3 = (
        [("Deck Gang 3", "story", BAYAN)]
        + [("Deck Gang 3", "recent_arrival", BAYAN)] * 2
        + [("Deck Gang 3", "new_contractor", SAHEL), ("Deck Gang 3", "new_contractor", BAYAN)]
        + [("Deck Gang 3", "exp_inhouse", MIRSAL)] * 4
        + [("Deck Gang 3", "mid_lasher", SAHEL)] * 2
        + [("Deck Gang 3", "mid_lasher", BAYAN)]
    )
    slots += gang3

    # The other pattern-A deck gangs: 44 experienced, 21 new contractors, 19 mid-tenure.
    deck_a = [f"Deck Gang {k}" for k in (1, 2, 4, 5, 6, 9, 10)]
    cohorts = ["exp_inhouse"] * 44 + ["new_contractor"] * 21 + ["mid_lasher"] * 19
    rng.shuffle(cohorts)
    new_emp = _employers({BAYAN: 12, SAHEL: 9}, rng)
    mid_emp = _employers({SAHEL: 11, BAYAN: 8}, rng)
    for i, cohort in enumerate(cohorts):
        crew = deck_a[i // 12]
        if cohort == "exp_inhouse":
            emp = MIRSAL
        elif cohort == "new_contractor":
            emp = new_emp.pop()
        else:
            emp = mid_emp.pop()
        slots.append((crew, cohort, emp))

    # Extended night rotation gangs 7 and 8: 22 experienced lashers and two mid-tenure.
    nights_emp = _employers({MIRSAL: 10, SAHEL: 12}, rng)
    for i in range(22):
        slots.append((f"Deck Gang {7 + i // 11}", "exp_nights", nights_emp.pop()))
    slots.append(("Deck Gang 7", "mid_lasher", SAHEL))
    slots.append(("Deck Gang 8", "mid_lasher", BAYAN))

    for i in range(34):
        slots.append((f"Mooring Gang {1 + i * 3 // 34}", "mooring", SAHEL))

    driver_cohorts = ["driver_refreshed"] * 58 + ["driver_overdue"] * 31 + ["driver_mid"] * 21
    rng.shuffle(driver_cohorts)
    driver_emp = _employers({MIRSAL: 50, BAYAN: 30, SAHEL: 30}, rng)
    for i, cohort in enumerate(driver_cohorts):
        slots.append((f"Yard Gang {1 + i // 11}", cohort, driver_emp.pop()))

    def add(crew: str, split: dict[str, int]) -> None:
        for emp in _employers(split, rng):
            slots.append((crew, "general", emp))

    add("QC Crew 1", {MIRSAL: 8})
    add("QC Crew 2", {MIRSAL: 8})
    add("Hold Crew", {SAHEL: 10})
    add("Hot Work Crew", {MIRSAL: 8})
    add("Ground Gang 1", {BAYAN: 12})
    add("Ground Gang 2", {BAYAN: 12})
    add("Reefer Team 1", {MIRSAL: 5, SAHEL: 5})
    add("Reefer Team 2", {MIRSAL: 5, SAHEL: 5})
    add("Workshop Team", {MIRSAL: 16})
    add("Inspection Team 1", {MIRSAL: 4, BAYAN: 6})
    add("Inspection Team 2", {MIRSAL: 4, BAYAN: 6})
    add("Housekeeping Crew", {BAYAN: 12})
    add("Gate Team", {MIRSAL: 10})

    assert len(slots) == 400, len(slots)

    workers: list[WorkerSpec] = []
    camp_c_in_gang3 = 0
    for crew_name, cohort, employer in slots:
        crew = crew_by_name[crew_name]
        competencies = COMPETENCY_FOR[crew.activity]
        if cohort == "story":
            first, last = "Arjun", "Thapa"
            hire, induction, courses = STORY_DATE - timedelta(days=122), "contractor", {}
        else:
            first, last = namer.next()
            hire, induction, courses = _cohort_record(cohort, rng)
        if employer != MIRSAL and induction == "site" and cohort.startswith("exp") is False:
            induction = "contractor"
        courses = {
            ("SITE_INDUCTION" if induction == "site" else "CONTRACTOR_INDUCTION"): hire,
            "HEAT_STRESS": hire + timedelta(days=2),
            **courses,
        }
        if cohort == "story":
            camp = "Camp Block C"
        elif crew_name == "Deck Gang 3" and camp_c_in_gang3 < 2 and cohort == "new_contractor":
            camp = "Camp Block C"
            camp_c_in_gang3 += 1
        elif employer == MIRSAL and rng.random() < 0.4:
            camp = None
        else:
            camp = CAMPS[int(rng.integers(0, len(CAMPS)))]
            if crew_name == "Deck Gang 3" and camp == "Camp Block C":
                camp = "Camp Block D"
        workers.append(
            WorkerSpec(
                first_name=first,
                last_name=last,
                employer=employer,
                cohort=cohort,
                crew=crew_name,
                competencies=list(competencies),
                induction=induction,
                hire_date=hire,
                arrival_date=hire,
                camp=camp,
                display_language="ne"
                if cohort == "story"
                else DISPLAY_LANGUAGES[int(rng.integers(0, len(DISPLAY_LANGUAGES)))],
                courses=courses,
                key="arjun" if cohort == "story" else None,
            )
        )
    return workers


def foreman_names(
    rng: np.random.Generator, crews: list[CrewDef], taken: set[str]
) -> dict[str, tuple[str, str]]:
    namer = _Namer(rng)
    namer.used |= taken
    names: dict[str, tuple[str, str]] = {}
    for crew in crews:
        if crew.name in ("Deck Gang 3", "Yard Gang 1"):
            continue
        names[crew.name] = namer.next()
    return names
