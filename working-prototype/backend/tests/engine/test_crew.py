from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.budget import apply_budget
from app.engine.crew_rules import CrewMember, check_crew_rules
from app.engine.run import run_scores
from app.models import Activity, Assignment, Person, Shift, SwapProposal
from app.models.roster import ShiftKind
from app.models.scores import RunKind, Tier


def _member(tier: Tier, days: int = 400, group: str | None = None, grade: int = 5) -> CrewMember:
    return CrewMember(
        assignment_id=0, tier=tier, r=1.0, acclimatisation_days=days, group_code=group, grade=grade
    )


def test_quarter_of_crew_on_controls_rule_in_heat_tier_2() -> None:
    crew = [_member(Tier.FIT_WITH_CONTROLS)] * 4 + [_member(Tier.FIT, group="EXP_INHOUSE")] * 8
    breaches = check_crew_rules(crew, heat_tier=2)
    assert [b.rule for b in breaches] == ["controls_share"]
    assert check_crew_rules(crew, heat_tier=1) == []
    three = [_member(Tier.FIT_WITH_CONTROLS)] * 3 + [_member(Tier.FIT, group="EXP_INHOUSE")] * 9
    assert check_crew_rules(three, heat_tier=3) == []


def test_arrivals_under_7_days_capped_at_2_per_gang() -> None:
    crew = [_member(Tier.FIT, days=3)] * 3 + [_member(Tier.FIT, group="EXP_INHOUSE")]
    assert [b.rule for b in check_crew_rules(crew, heat_tier=0)] == ["arrivals_cap"]
    two = [_member(Tier.FIT, days=3)] * 2 + [_member(Tier.FIT, group="EXP_INHOUSE")]
    assert check_crew_rules(two, heat_tier=0) == []


def test_high_hazard_task_keeps_one_experienced_worker() -> None:
    crew = [_member(Tier.FIT, group="NEW_CONTRACTOR")] * 5
    assert [b.rule for b in check_crew_rules(crew, heat_tier=0)] == ["experienced_present"]
    low = [_member(Tier.FIT, group="NEW_CONTRACTOR", grade=3)] * 5
    assert check_crew_rules(low, heat_tier=0) == []


def test_budget_shows_three_and_rolls_rest_into_brief() -> None:
    items = [{"r": r} for r in (1.95, 2.3, 1.91, 2.0, 1.92)]
    shown, rolled = apply_budget(items, limit=3)
    assert [i["r"] for i in shown] == [2.3, 2.0, 1.95]
    assert [i["r"] for i in rolled] == [1.92, 1.91]


def test_marco_swap_proposal_is_ground_twist_lock_handling(scenario: Session) -> None:
    shift = scenario.scalars(
        select(Shift).where(Shift.date == date(2026, 7, 29), Shift.kind == ShiftKind.NIGHT)
    ).one()
    run = run_scores(scenario, shift.id, RunKind.EVENING)
    marco = scenario.scalars(
        select(Person).where(Person.email == "marco.villanueva@mirsalterminals.com")
    ).one()
    proposal = scenario.scalars(
        select(SwapProposal)
        .join(Assignment, Assignment.id == SwapProposal.assignment_id)
        .where(SwapProposal.run_id == run.id, Assignment.person_id == marco.id)
    ).one()
    target = scenario.get_one(Activity, proposal.to_activity_id)
    assert target.code == "TWIST_GROUND"
    proposals = scenario.scalars(select(SwapProposal).where(SwapProposal.run_id == run.id)).all()
    assert 1 <= len(proposals) <= 3
