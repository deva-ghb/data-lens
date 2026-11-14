"""Behavioural group definitions (concept doc section 5.4).

A group is defined by training pathway, tenure and roster only. Origin, nationality,
religion, ethnicity and language are never inputs.
"""

from dataclasses import dataclass
from typing import Any


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
