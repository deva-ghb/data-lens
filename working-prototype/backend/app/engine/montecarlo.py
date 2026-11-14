"""Split tomorrow's risk between conditions and crew.

A Monte Carlo run over the uncertain inputs: the forecast WBGT (normal, sd 1.5 C by
default), attendance (from absence history, about 3 percent) and how each worker will
feel at check-in. The share of variance that comes from conditions is the argument for
moving a work window; the share from the crew is the argument for swapping a worker.
"""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.layers import hazards_of, peak_wbgt
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


def _tiers(wbgt: np.ndarray) -> np.ndarray:
    return np.searchsorted(np.array(TIER_FLOORS), wbgt, side="right")


def split_risk(
    session: Session, shift_id: int, n: int = 2000, seed: int = 7, wbgt_sd: float = 1.5
) -> SplitResult:
    run = latest_run(session, shift_id)
    if run is None:
        raise LookupError("Score the shift before splitting its risk.")
    weights = load_weights(session)
    shift = session.get_one(Shift, shift_id)
    rows = session.execute(
        select(AssignmentScore.r, AssignmentScore.drivers_json, Assignment.activity_id)
        .join(Assignment, Assignment.id == AssignmentScore.assignment_id)
        .where(AssignmentScore.run_id == run.id)
    ).all()
    peak, _ = peak_wbgt(
        session,
        shift.start_at - timedelta(hours=12),
        shift.end_at,
        ConditionsSource(run.conditions_source),
    )
    r = np.array([row.r for row in rows], dtype=float)
    heat_now = np.array(
        [
            next((d["multiplier"] for d in row.drivers_json if d.get("name") == "heat"), 1.0)
            for row in rows
        ]
    )
    hazard_cache: dict[int, list[str]] = {}
    heat_sens, acute_sens = [], []
    for row in rows:
        hazards = hazard_cache.setdefault(row.activity_id, hazards_of(session, row.activity_id))
        heat_sens.append(weights.sensitivity(hazards, "heat_strain"))
        acute_sens.append(weights.sensitivity(hazards, "acute"))
    heat_sens_a, acute_sens_a = np.array(heat_sens), np.array(acute_sens)
    base = r / heat_now
    heat_by_tier = np.array([weights.heat_by_tier[t] for t in sorted(weights.heat_by_tier)])
    rng = np.random.default_rng(seed)
    centre = peak if peak is not None else 30.0

    def conditions(samples: int) -> np.ndarray:
        wbgt = rng.normal(centre, wbgt_sd, samples)
        c = heat_by_tier[_tiers(wbgt)]
        return 1 + np.outer(c - 1, heat_sens_a)  # samples x workers

    def crew(samples: int) -> np.ndarray:
        present = rng.random((samples, len(r))) > ABSENCE_RATE
        tired = rng.random((samples, len(r))) < TIRED_RATE
        return present * (1 + tired * (weights.acute["tired"] - 1) * acute_sens_a)

    mean_heat = conditions(4000).mean(axis=0)
    mean_crew = crew(4000).mean(axis=0)
    full = (base * conditions(n) * crew(n)).sum(axis=1)
    cond_only = (base * conditions(n) * mean_crew).sum(axis=1)
    crew_only = (base * mean_heat * crew(n)).sum(axis=1)
    var_c, var_w = float(cond_only.var()), float(crew_only.var())
    total_var = var_c + var_w
    conditions_share = var_c / total_var if total_var > 0 else 0.5
    return SplitResult(
        total_expected=round(float(full.mean()), 2),
        conditions_share=round(conditions_share, 3),
        crew_share=round(1 - conditions_share, 3),
        p10=round(float(np.percentile(full, 10)), 2),
        p90=round(float(np.percentile(full, 90)), 2),
        workers=len(r),
        peak_wbgt=peak,
    )
