"""Reference catalogue for the synthetic Mirsal Terminals site.

Everything here is fixed reference data: the activity register, hazards, competencies,
training courses, behavioural group definitions, employers, zones and the named users.
Records (rosters, observations, clinic visits and so on) are generated in seed/generate.py.
All names, places and organisations are fictional.
"""

from dataclasses import dataclass, field
from typing import Any

EMAIL_DOMAIN = "mirsalterminals.com"
PASSWORD = "welcome@123"


@dataclass(frozen=True)
class HazardDef:
    code: str
    name: str


HAZARDS: list[HazardDef] = [
    HazardDef("FALL_HEIGHT", "Fall from height"),
    HazardDef("STRUCK_PLANT", "Struck by or caught between mobile plant"),
    HazardDef("DROPPED_LOAD", "Dropped load and lifting"),
    HazardDef("HEAT_ILLNESS", "Heat illness and collapse"),
    HazardDef("MANUAL_HANDLING", "Manual handling injury"),
    HazardDef("HOT_WORK_CONFINED", "Hot work and confined space"),
]


@dataclass(frozen=True)
class CompetencyDef:
    code: str
    name: str


COMPETENCIES: list[CompetencyDef] = [
    CompetencyDef("LASHING", "Lashing and unlashing"),
    CompetencyDef("QC_OPERATOR", "Quay crane operator"),
    CompetencyDef("MOORING", "Mooring and unmooring"),
    CompetencyDef("CONFINED_SPACE", "Confined space entry"),
    CompetencyDef("HOT_WORK", "Hot work"),
    CompetencyDef("REACH_STACKER", "Reach stacker operator"),
    CompetencyDef("TT_DRIVER", "Terminal tractor driver"),
    CompetencyDef("GROUND_OPS", "Ground operations"),
    CompetencyDef("REEFER", "Reefer technician"),
    CompetencyDef("MECHANIC", "Workshop mechanic"),
    CompetencyDef("INSPECTION", "Container inspection"),
    CompetencyDef("GATE", "Gate operations"),
]

# Training courses that matter to the model (refreshers and inductions).
COURSES = {
    "SITE_INDUCTION": "Mirsal site induction",
    "CONTRACTOR_INDUCTION": "Contractor induction",
    "LASHING_SEQUENCE": "Terminal lashing sequence module",
    "HEIGHT_REFRESHER": "Work at height refresher",
    "DRIVING_REFRESHER": "Mobile plant driving refresher",
    "HEAT_STRESS": "Heat stress awareness",
}


@dataclass(frozen=True)
class ActivityDef:
    code: str
    name: str
    grade: int
    exposure_hours_week: float
    severity: int
    competency: str
    hazards: list[str]
    swp_items: list[str]
    zone_kind: str  # where the work happens: "berth", "yard_block" or "site"
    lower_hazard_alternative: str | None = None


ACTIVITIES: list[ActivityDef] = [
    ActivityDef(
        "LASH_DECK",
        "Lashing at height on deck",
        5,
        1440,
        5,
        "LASHING",
        ["FALL_HEIGHT", "DROPPED_LOAD", "HEAT_ILLNESS", "MANUAL_HANDLING"],
        [
            "Toolbox talk held at the gangway before boarding",
            "Harness inspected and signed off by the wearer",
            "Clip on to the lashing platform rail before climbing",
            "Three points of contact on every ladder",
            "No lashing above the third tier without a platform",
            "Lashing bars passed hand to hand, never thrown",
            "Turnbuckles tightened in the terminal's lashing sequence",
            "Keep clear of the spreader path and the crane's swing zone",
            "Signal the crane driver before stepping into a bay",
            "Deck lighting checked before night work starts",
            "Work-rest cycle set from deck-level WBGT",
            "Water point within 30 metres of the working bay",
            "Buddy in sight at all times above the second tier",
            "Report any damaged lashing gear before use",
        ],
        "berth",
        lower_hazard_alternative="TWIST_GROUND",
    ),
    ActivityDef(
        "QC_OPS",
        "Quay crane operation",
        5,
        672,
        5,
        "QC_OPERATOR",
        ["DROPPED_LOAD", "FALL_HEIGHT"],
        [
            "Pre-start check of brakes, limits and anemometer",
            "Wind speed checked against the operating limit",
            "Radio check with the signaller before the first move",
            "No load over people on the quay or deck",
            "Cab access by ladder with three points of contact",
            "Break every two hours in the cab",
        ],
        "berth",
    ),
    ActivityDef(
        "MOORING",
        "Mooring and unmooring",
        5,
        336,
        5,
        "MOORING",
        ["STRUCK_PLANT", "MANUAL_HANDLING", "HEAT_ILLNESS"],
        [
            "Stand outside the snap-back zone of every line",
            "Radio contact with the pilot and the vessel",
            "Lines handled by at least two people",
            "Life jacket worn within two metres of the quay edge",
            "Bollards and fairleads checked before the vessel arrives",
        ],
        "berth",
    ),
    ActivityDef(
        "HOLD_CONFINED",
        "Hold cleaning in a confined space",
        5,
        168,
        5,
        "CONFINED_SPACE",
        ["HOT_WORK_CONFINED", "HEAT_ILLNESS"],
        [
            "Gas test before entry and every 30 minutes",
            "Standby person at the hatch for the whole entry",
            "Entry permit signed and displayed at the access",
            "Rescue tripod and harness rigged before entry",
            "Maximum 45 minutes inside before a cool-down break",
        ],
        "berth",
    ),
    ActivityDef(
        "HOT_WORK",
        "Hot work in the workshop",
        4,
        240,
        4,
        "HOT_WORK",
        ["HOT_WORK_CONFINED", "HEAT_ILLNESS"],
        [
            "Hot work permit issued before striking an arc",
            "Fire watch in place during and 30 minutes after",
            "Combustibles cleared to 11 metres",
            "Extinguisher within reach of the work",
        ],
        "site",
    ),
    ActivityDef(
        "REACH_STACKER",
        "Reach stacker operation",
        4,
        960,
        4,
        "REACH_STACKER",
        ["STRUCK_PLANT", "DROPPED_LOAD"],
        [
            "Walk-around check before the shift",
            "No pedestrians inside the stacking lane",
            "Load within the rated chart for the boom angle",
            "Horn at every blind corner and aisle end",
            "Speed limit 15 km/h in the yard",
        ],
        "yard_block",
    ),
    ActivityDef(
        "TT_DRIVING",
        "Terminal tractor driving",
        4,
        2400,
        4,
        "TT_DRIVER",
        ["STRUCK_PLANT"],
        [
            "Seat belt on before moving",
            "Speed limit 25 km/h on the quay apron, 15 km/h in the yard",
            "Stop at every crossing marked for pedestrians",
            "No phone use while the engine is running",
            "Report near misses at the end of every run",
        ],
        "yard_block",
    ),
    ActivityDef(
        "TWIST_GROUND",
        "Ground twist-lock handling",
        3,
        960,
        3,
        "LASHING",
        ["STRUCK_PLANT", "MANUAL_HANDLING", "HEAT_ILLNESS"],
        [
            "Stand in the marked safe bay while the spreader lands",
            "Hand signal to the crane before approaching the box",
            "High-visibility vest and hard hat at all times",
            "Water point within 30 metres",
        ],
        "berth",
    ),
    ActivityDef(
        "REEFER",
        "Reefer plugging and monitoring",
        3,
        480,
        3,
        "REEFER",
        ["STRUCK_PLANT", "HEAT_ILLNESS"],
        [
            "Isolate power before unplugging",
            "Use the reefer rack walkway, not the stack",
            "Check every plug for heat damage",
        ],
        "yard_block",
    ),
    ActivityDef(
        "WORKSHOP_MECH",
        "Workshop mechanical maintenance",
        3,
        720,
        3,
        "MECHANIC",
        ["MANUAL_HANDLING", "DROPPED_LOAD"],
        [
            "Lock out and tag out before any repair",
            "Use the overhead hoist for loads over 25 kg",
            "Stands under any raised vehicle",
        ],
        "site",
    ),
    ActivityDef(
        "CONTAINER_INSPECT",
        "Container inspection and sealing",
        2,
        720,
        2,
        "INSPECTION",
        ["STRUCK_PLANT", "HEAT_ILLNESS"],
        [
            "Inspect only in the marked inspection lane",
            "Seal numbers recorded on the handheld",
        ],
        "yard_block",
    ),
    ActivityDef(
        "YARD_HOUSEKEEPING",
        "Yard housekeeping",
        2,
        480,
        2,
        "GROUND_OPS",
        ["STRUCK_PLANT", "MANUAL_HANDLING", "HEAT_ILLNESS"],
        [
            "Work only in lanes closed to traffic",
            "Lift debris with the grab, not by hand",
        ],
        "yard_block",
    ),
    ActivityDef(
        "GATE_CLERK",
        "Gate clerk",
        1,
        336,
        1,
        "GATE",
        ["STRUCK_PLANT"],
        [
            "Stay inside the booth while trucks move",
            "Use the intercom for driver questions",
        ],
        "site",
    ),
]


@dataclass(frozen=True)
class GroupDef:
    code: str
    name: str
    defined_by: str
    proposal: str


GROUPS: list[GroupDef] = [
    GroupDef(
        "EXP_INHOUSE",
        "Experienced lashers, in-house induction",
        "24 months or more, site induction, refresher current",
        "Keep one on every high-hazard task",
    ),
    GroupDef(
        "NEW_CONTRACTOR",
        "New arrivals, contractor induction only",
        "Under 6 months, no site refresher yet",
        "Site height refresher before the next night rotation; cap at two per gang; "
        "add the lashing sequence to the contractor induction",
    ),
    GroupDef(
        "EXP_NIGHTS",
        "Experienced lashers, extended night rotation",
        "24 months or more, 4 or more nights in a row within 14 days",
        "Roster rule: no fourth night in a row on grade 5 work in heat tier 2 or above",
    ),
    GroupDef(
        "YARD_REFRESHED",
        "Yard drivers, recent refresher",
        "Driving refresher in the last 6 months",
        "No change; the evidence for refreshing the next group",
    ),
    GroupDef(
        "YARD_OVERDUE",
        "Yard drivers, refresher overdue",
        "Driving refresher more than 18 months ago",
        "Book the refresher within 30 days; pair at changeover until then",
    ),
    GroupDef(
        "MOORING_ALL",
        "Mooring crews, all",
        "All mooring-competent workers",
        "No change",
    ),
]

YARD_DRIVING = {"TT_DRIVER", "REACH_STACKER"}


def classify_group(history: dict[str, Any]) -> str | None:
    """The behavioural group a person belongs to, from training, tenure and roster only.

    `history` keys: tenure_months, induction ("site" or "contractor"), competencies (set),
    courses (set of completed course codes), nights_in_row_max_14d, and months_since
    (course code to months since last completed). Names, origin and language are not inputs.
    """
    competencies: set[str] = set(history["competencies"])
    months_since: dict[str, float] = history.get("months_since", {})
    tenure = history["tenure_months"]
    if "MOORING" in competencies:
        return "MOORING_ALL"
    if "LASHING" in competencies:
        if tenure < 6 and history["induction"] == "contractor":
            if "HEIGHT_REFRESHER" not in history["courses"]:
                return "NEW_CONTRACTOR"
        if tenure >= 24:
            if history["nights_in_row_max_14d"] >= 4:
                return "EXP_NIGHTS"
            refresher_age = months_since.get("HEIGHT_REFRESHER")
            if history["induction"] == "site" and refresher_age is not None and refresher_age <= 12:
                return "EXP_INHOUSE"
        return None
    if competencies & YARD_DRIVING:
        age = months_since.get("DRIVING_REFRESHER")
        if age is not None and age <= 6:
            return "YARD_REFRESHED"
        if age is None or age > 18:
            return "YARD_OVERDUE"
    return None


@dataclass(frozen=True)
class EmployerDef:
    name: str
    kind: str
    logo_key: str


EMPLOYERS: list[EmployerDef] = [
    EmployerDef("Mirsal Terminals", "in_house", "mirsal"),
    EmployerDef("Sahel Marine Services", "contractor", "sahel"),
    EmployerDef("Bayan Manpower Contracting", "contractor", "bayan"),
]


@dataclass(frozen=True)
class ZoneDef:
    name: str
    kind: str
    parent: str | None = None


ZONES: list[ZoneDef] = [
    ZoneDef("Mirsal Port District", "district"),
    ZoneDef("Mirsal Village District", "district"),
    *[ZoneDef(f"Berth {n}", "berth", "Mirsal Port District") for n in range(1, 5)],
    *[ZoneDef(f"Yard Block {n}", "yard_block", "Mirsal Port District") for n in range(1, 7)],
    *[ZoneDef(f"Camp Block {c}", "camp_block", "Mirsal Village District") for c in "ABCDE"],
]

CLINIC_NAME = "Mirsal Village Clinic"
CLINIC_ZONE = "Camp Block A"
COOLING_UNITS_PER_BLOCK = 40


@dataclass(frozen=True)
class KeyUser:
    first_name: str
    last_name: str
    role: str
    employer: str
    job_title: str
    induction: str = "site"
    camp: str | None = None
    display_language: str = "en"
    note: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def email(self) -> str:
        local = f"{self.first_name}.{self.last_name}".lower().replace(" ", "").replace("'", "")
        return f"{local}@{EMAIL_DOMAIN}"


KEY_USERS: list[KeyUser] = [
    KeyUser("Hessa", "AlMansoori", "admin", "Mirsal Terminals", "People systems administrator"),
    KeyUser(
        "Layla", "Haddad", "hse_head", "Mirsal Terminals", "Head of health, safety and environment"
    ),
    KeyUser("Daniel", "Mensah", "planner", "Mirsal Terminals", "Shift planner"),
    KeyUser("Khalid", "AlNuaimi", "shift_manager", "Mirsal Terminals", "Shift manager"),
    KeyUser("Priya", "Raman", "permit_issuer", "Mirsal Terminals", "Permit issuer"),
    KeyUser(
        "Joseph",
        "Kariuki",
        "foreman",
        "Sahel Marine Services",
        "Deck foreman, Gang 3",
        extra={"gang": "Deck Gang 3"},
    ),
    KeyUser(
        "Tomas",
        "Reyes",
        "foreman",
        "Mirsal Terminals",
        "Yard foreman",
        extra={"gang": "Yard Gang 1"},
    ),
    KeyUser("Sara", "Ibrahim", "clinician", "Mirsal Terminals", "Occupational health physician"),
    KeyUser(
        "Ahmed", "AlShamsi", "authority", "Mirsal Terminals", "District health and labour liaison"
    ),
    KeyUser(
        "Arjun",
        "Thapa",
        "worker",
        "Bayan Manpower Contracting",
        "Lasher",
        induction="contractor",
        camp="Camp Block C",
        display_language="ne",
        note="The lasher in the walkthrough: new arrival, contractor induction only, "
        "third night in a row on 29 July, height refresher not done.",
        extra={"gang": "Deck Gang 3", "arrived_months_ago": 4},
    ),
]
