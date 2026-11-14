"""Crew rules (concept doc section 6.3), checked per gang on a shift."""

from dataclasses import dataclass

from app.models.scores import Tier

EXPERIENCED_GROUPS = {"EXP_INHOUSE", "EXP_NIGHTS"}


@dataclass(frozen=True)
class CrewMember:
    assignment_id: int
    tier: Tier
    r: float
    acclimatisation_days: int
    group_code: str | None
    grade: int


@dataclass(frozen=True)
class RuleBreach:
    rule: str
    detail: str


def check_crew_rules(crew: list[CrewMember], heat_tier: int) -> list[RuleBreach]:
    breaches: list[RuleBreach] = []
    if not crew:
        return breaches
    high_hazard = max(m.grade for m in crew) >= 4
    on_controls = sum(1 for m in crew if m.tier == Tier.FIT_WITH_CONTROLS)
    if high_hazard and heat_tier >= 2 and on_controls * 4 > len(crew):
        breaches.append(
            RuleBreach(
                "controls_share",
                f"{on_controls} of {len(crew)} on extra controls; "
                f"in heat tier {heat_tier} at most a quarter of a high-hazard crew "
                "may be on extra controls",
            )
        )
    arrivals = sum(1 for m in crew if m.acclimatisation_days < 7)
    if arrivals > 2:
        breaches.append(
            RuleBreach(
                "arrivals_cap",
                f"{arrivals} arrived under 7 days ago; at most 2 recent arrivals per gang",
            )
        )
    if high_hazard and not any(m.group_code in EXPERIENCED_GROUPS for m in crew):
        breaches.append(
            RuleBreach(
                "experienced_present",
                "No experienced worker; every high-hazard crew needs "
                "at least one experienced worker",
            )
        )
    return breaches
