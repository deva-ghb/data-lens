"""Readiness as people other than the planner see it: counts, never names."""

from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.run import latest_run
from app.models import Assignment, AssignmentScore, Permit, SwapProposal
from app.models.scores import SwapStatus, Tier

TIER_KEYS = ["fit", "fit_with_controls", "reassign", "refer", "unknown"]


def permit_readiness(session: Session, permit: Permit) -> dict[str, Any]:
    """The crew behind a permit as counts, its status colour, top drivers and confidence."""
    run = latest_run(session, permit.shift_id)
    crew = session.scalars(
        select(Assignment.id).where(
            Assignment.shift_id == permit.shift_id,
            Assignment.activity_id == permit.activity_id,
            Assignment.zone_id == permit.zone_id,
        )
    ).all()
    counts = dict.fromkeys(TIER_KEYS, 0)
    drivers: Counter[str] = Counter()
    confidences: list[float] = []
    open_reassign = 0
    if run is not None and crew:
        scores = session.scalars(
            select(AssignmentScore).where(
                AssignmentScore.run_id == run.id, AssignmentScore.assignment_id.in_(crew)
            )
        ).all()
        latest: dict[int, SwapStatus] = {}
        for sp in session.scalars(
            select(SwapProposal)
            .where(SwapProposal.assignment_id.in_(crew))
            .order_by(SwapProposal.id)
        ):
            latest[sp.assignment_id] = sp.status
        settled = {
            aid for aid, st in latest.items() if st in (SwapStatus.APPROVED, SwapStatus.DECLINED)
        }
        for s in scores:
            counts[s.tier.value] += 1
            confidences.append(s.confidence)
            if s.tier == Tier.REASSIGN and s.assignment_id not in settled:
                open_reassign += 1
            for d in s.drivers_json:
                if d.get("layer") in ("condition", "control") and d.get("contribution", 0) > 0.02:
                    drivers[d["reason"]] += 1
    if run is None and crew:
        status = "unscored"  # nobody has been scored: never shown as ready
    elif open_reassign:
        status = "red"
    elif counts["fit_with_controls"] or counts["refer"] or counts["unknown"]:
        status = "amber"
    else:
        status = "green"
    return {
        "crew_size": len(crew),
        "readiness": counts,
        "crew_status": status,
        "open_reassignments": open_reassign,
        "top_drivers": [reason for reason, _ in drivers.most_common(3)],
        "confidence": round(sum(confidences) / len(confidences), 2) if confidences else None,
        "scored": run is not None,
    }
