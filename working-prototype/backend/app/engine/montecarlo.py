"""Split tomorrow's risk between conditions and crew, with an uncertainty band.

The split answers "is this a night to move the work window, or to swap people?". For
each scored worker, the risk above baseline is divided between the condition layer
(heat, night, dust, pace, camp recovery) and the profile layer (the person's readiness),
in proportion to each layer's share of log R. The crew's totals give the shares.

A Monte Carlo run over the uncertain inputs then gives a band around tomorrow's total
excess risk: the forecast WBGT (normal, sd 1.5 C by default), attendance (about 3 percent
absent) and tired check-ins (about 10 percent). If there is no forecast for the shift,
the result says so instead of assuming one.
"""

from dataclasses import dataclass
from datetime import timedelta
from math import log

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.layers import hazards_of, live_window, peak_wbgt
from app.engine.run import latest_run
from app.engine.weights import load_weights
from app.feeds.wbgt import TIER_FLOORS
from app.models import Assignment, AssignmentScore, Shift
from app.models.scores import ConditionsSource

ABSENCE_RATE = 0.03
TIRED_RATE = 0.10


@dataclass(frozen=True)
class SplitResult:
    total_expected: float
    conditions_share: float
    crew_share: float
    p10: float
    p90: float
    workers: int
    peak_wbgt: float | None
    forecast_missing: bool


def split_risk(
    session: Session, shift_id: int, n: int = 2000, seed: int = 7, wbgt_sd: float = 1.5
) -> SplitResult:
    run = latest_run(session, shift_id)
    if run is None:
        raise LookupError("Score the shift before splitting its risk.")
    weights = load_weights(session)
    shift = session.get_one(Shift, shift_id)
    rows = session.execute(
        select(
            AssignmentScore.r,
            AssignmentScore.condition,
            AssignmentScore.profile,
            AssignmentScore.drivers_json,
            Assignment.activity_id,
        )
        .join(Assignment, Assignment.id == AssignmentScore.assignment_id)
        .where(AssignmentScore.run_id == run.id)
    ).all()

    source = ConditionsSource(run.conditions_source)
    window = (shift.start_at - timedelta(hours=12), shift.end_at)
    if source == ConditionsSource.LIVE:
        span = live_window(session)
        if span is not None:
            window = (span[0], min(span[0] + timedelta(hours=36), span[1]))
    peak, _ = peak_wbgt(session, window[0], window[1], source)

    cond_log = sum(max(log(row.condition), 0.0) for row in rows)
    prof_log = sum(max(log(row.profile), 0.0) for row in rows)
    total_log = cond_log + prof_log
    conditions_share = cond_log / total_log if total_log > 0 else 0.5

    r = np.array([row.r for row in rows], dtype=float)
    heat_now = np.array(
        [
            next((d["multiplier"] for d in row.drivers_json if d.get("name") == "heat"), 1.0)
            for row in rows
        ]
    )
    hazards: dict[int, list[str]] = {}
    heat_sens = np.array(
        [
            weights.sensitivity(
                hazards.setdefault(row.activity_id, hazards_of(session, row.activity_id)),
                "heat_strain",
            )
            for row in rows
        ]
    )
    acute_sens = np.array([weights.sensitivity(hazards[row.activity_id], "acute") for row in rows])
    rng = np.random.default_rng(seed)
    base = r / heat_now
    heat_by_tier = np.array([weights.heat_by_tier[t] for t in sorted(weights.heat_by_tier)])
    if peak is None:
        heat = np.repeat(heat_now[None, :], n, axis=0)
    else:
        wbgt = rng.normal(peak, wbgt_sd, n)
        tiers = np.searchsorted(np.array(TIER_FLOORS), wbgt, side="right")
        heat = 1 + np.outer(heat_by_tier[tiers] - 1, heat_sens)
    present = rng.random((n, len(r))) > ABSENCE_RATE
    tired = rng.random((n, len(r))) < TIRED_RATE
    crew = present * (1 + tired * (weights.acute["tired"] - 1) * acute_sens)
    excess = ((base * heat * crew) - present).clip(min=0).sum(axis=1)
    return SplitResult(
        total_expected=round(float(excess.mean()), 2),
        conditions_share=round(conditions_share, 3),
        crew_share=round(1 - round(conditions_share, 3), 3),
        p10=round(float(np.percentile(excess, 10)), 2),
        p90=round(float(np.percentile(excess, 90)), 2),
        workers=len(r),
        peak_wbgt=peak,
        forecast_missing=peak is None,
    )
