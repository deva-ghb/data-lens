"""Versioned model weights.

Weights live in the database as `WeightsVersion` rows. Version zero comes from
`seed/weights_v0.json`, the single source for every number the engine uses.
A later version (for example the workshop output) is a new row; the engine reads
the active one unless a version is named.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WeightsVersion
from app.models.governance import WeightsStatus

Level = Literal["H", "M", "L"]
WEIGHTS_V0_PATH = Path(__file__).resolve().parents[2] / "seed" / "weights_v0.json"


@dataclass(frozen=True)
class Weights:
    id: int
    version: str
    dimensions: list[str]
    sens: dict[str, dict[str, Level]]
    sens_value: dict[str, float]
    thresholds: dict[int, tuple[float, float]]
    factor_caps: dict[str, float]
    group_cap: float
    control_formula_k: float
    control_window_days: int
    fatigue_by_night: dict[int, float]
    short_sleep_step: float
    heat_by_tier: dict[int, float]
    heat_strain: dict[str, float]
    competency: dict[str, float]
    acute: dict[str, float]
    physical: dict[str, float]
    condition_terms: dict[str, dict[str, Any]]

    def sensitivity(self, hazard_codes: list[str], dimension: str) -> float:
        """How strongly an activity reacts to a deficit: its most sensitive hazard decides."""
        values = [self.sens_value[self.sens[h][dimension]] for h in hazard_codes]
        return max(values, default=self.sens_value["L"])

    def fatigue_for_nights(self, nights: int) -> float:
        if nights <= 0:
            return 1.0
        top = max(self.fatigue_by_night)
        return self.fatigue_by_night[min(nights, top)]


def _from_body(row_id: int, body: dict[str, Any]) -> Weights:
    return Weights(
        id=row_id,
        version=body["version"],
        dimensions=list(body["dimensions"]),
        sens=body["sens"],
        sens_value=dict(body["sens_value"]),
        thresholds={int(g): (float(t[0]), float(t[1])) for g, t in body["thresholds"].items()},
        factor_caps=dict(body["factor_caps"]),
        group_cap=float(body["group_cap"]),
        control_formula_k=float(body["control_formula_k"]),
        control_window_days=int(body["control_window_days"]),
        fatigue_by_night={int(k): float(v) for k, v in body["fatigue_by_night"].items()},
        short_sleep_step=float(body["short_sleep_step"]),
        heat_by_tier={int(k): float(v) for k, v in body["heat_by_tier"].items()},
        heat_strain=dict(body["heat_strain"]),
        competency=dict(body["competency"]),
        acute=dict(body["acute"]),
        physical=dict(body["physical"]),
        condition_terms=body["condition_terms"],
    )


def read_v0_body() -> dict[str, Any]:
    return json.loads(WEIGHTS_V0_PATH.read_text())


def ensure_weights_v0(session: Session) -> WeightsVersion:
    """Store weights v0 as the active version if it is not there yet."""
    existing = session.scalar(select(WeightsVersion).where(WeightsVersion.version == "v0"))
    if existing is not None:
        return existing
    row = WeightsVersion(version="v0", status=WeightsStatus.ACTIVE, body_json=read_v0_body())
    session.add(row)
    session.flush()
    return row


def load_weights(session: Session, version: str | None = None) -> Weights:
    """The active weights, or a named version."""
    query = select(WeightsVersion)
    if version is None:
        query = query.where(WeightsVersion.status == WeightsStatus.ACTIVE)
    else:
        query = query.where(WeightsVersion.version == version)
    row = session.scalar(query)
    if row is None:
        raise LookupError(f"No weights found for {version or 'the active version'}.")
    return _from_body(row.id, row.body_json)
