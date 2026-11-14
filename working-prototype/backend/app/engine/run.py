"""Engine runs: the evening run on tomorrow's roster, the shift-start re-score, or a
re-score a planner starts. Each run scores every graded assignment on the shift and
proposes swaps within the alert budget."""

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import audit
from app.clock import site_now
from app.engine.crew_rules import check_crew_rules
from app.engine.score import ScoreResult, score
from app.engine.swaps import crews_from, propose_swaps
from app.engine.weights import load_weights
from app.models import Activity, Assignment, AssignmentScore, Person, ScoreRun
from app.models.scores import ConditionsSource, RunKind

CACHE_PREFIXES = ("memberships", "group_rates", "control_rates")


def clear_engine_caches(session: Session) -> None:
    for key in list(session.info):
        if isinstance(key, tuple) and key and key[0] in CACHE_PREFIXES:
            del session.info[key]


def run_scores(
    session: Session,
    shift_id: int,
    kind: RunKind,
    conditions_source: ConditionsSource = ConditionsSource.SCENARIO,
    actor: Person | None = None,
) -> ScoreRun:
    clear_engine_caches(session)
    weights = load_weights(session)
    run = ScoreRun(
        kind=kind,
        shift_id=shift_id,
        weights_version_id=weights.id,
        ran_at=site_now(session),
        conditions_source=conditions_source,
    )
    session.add(run)
    session.flush()
    assignment_ids = session.scalars(
        select(Assignment.id)
        .join(Activity, Activity.id == Assignment.activity_id)
        .where(Assignment.shift_id == shift_id, Activity.grade >= 3)
        .order_by(Assignment.id)
    ).all()
    results: list[ScoreResult] = []
    for assignment_id in assignment_ids:
        result = score(
            session,
            assignment_id,
            weights,
            conditions_source,
            require_checkin=kind == RunKind.SHIFT_START,
            live=kind != RunKind.EVENING,
        )
        if result is None:
            continue
        results.append(result)
        session.add(
            AssignmentScore(
                run_id=run.id,
                assignment_id=assignment_id,
                intrinsic=result.intrinsic,
                control=result.control,
                condition=result.condition,
                profile=result.profile,
                r=result.r,
                tier=result.tier,
                drivers_json=[
                    *result.drivers,
                    {
                        "layer": "summary",
                        "name": "reason",
                        "reason": result.reason,
                        "late_feeds": result.late_feeds,
                        "contribution": -1,
                    },
                ],
                confidence=result.confidence,
                group_step_limited=result.group_step_limited,
            )
        )
    session.flush()
    proposals = propose_swaps(
        session, run.id, results, weights, conditions_source, live=kind != RunKind.EVENING
    )
    breaches = crew_breaches(results)
    tiers = Counter(r.tier.value for r in results)
    audit(
        session,
        actor,
        "score_run",
        "shift",
        str(shift_id),
        evidence={
            "kind": kind.value,
            "conditions": conditions_source.value,
            "scored": len(results),
            "tiers": dict(tiers),
            "swaps_proposed": len(proposals),
            "crew_rule_breaches": breaches,
        },
        model_version=f"weights {weights.version}",
    )
    return run


def crew_breaches(results: list[ScoreResult]) -> list[dict[str, object]]:
    """Every crew rule a shift's crews break, by gang and activity."""
    out: list[dict[str, object]] = []
    heat = max((r.heat_tier or 0 for r in results), default=0)
    for (gang_id, activity_id), crew in crews_from(results).items():
        for breach in check_crew_rules(crew, heat):
            out.append(
                {
                    "gang_id": gang_id,
                    "activity_id": activity_id,
                    "rule": breach.rule,
                    "detail": breach.detail,
                }
            )
    return out


def latest_run(session: Session, shift_id: int) -> ScoreRun | None:
    return session.scalars(
        select(ScoreRun).where(ScoreRun.shift_id == shift_id).order_by(ScoreRun.id.desc())
    ).first()
