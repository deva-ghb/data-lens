"""Activities and intrinsic risk, and the behavioural groups (rates only, never members)."""

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.common import SessionDep, not_found, require_scope
from app.clock import site_now
from app.engine.group_defs import GROUPS
from app.engine.groups import group_rates
from app.engine.layers import UABC_KINDS, control, hazards_of
from app.engine.weights import load_weights
from app.models import Activity, Hazard, Incident, NearMiss, Observation, Person, SwpItem
from app.models.records import RecordStatus

router = APIRouter(tags=["activities"])
STAFF = ("site_tiers", "aggregates", "permit_counts", "swap_proposals")


def _uabc(session, activity_id: int, since) -> dict[str, int]:  # type: ignore[no-untyped-def]
    counts = Counter(
        k.value
        for k in session.scalars(
            select(Observation.kind).where(
                Observation.activity_id == activity_id,
                Observation.kind.in_(UABC_KINDS),
                Observation.at >= since,
            )
        )
    )
    near = session.scalars(
        select(NearMiss.id).where(
            NearMiss.activity_id == activity_id,
            NearMiss.at >= since,
            NearMiss.status == RecordStatus.CLOSED,
        )
    ).all()
    incidents = session.scalars(
        select(Incident.id).where(
            Incident.activity_id == activity_id,
            Incident.at >= since,
            Incident.status == RecordStatus.CLOSED,
        )
    ).all()
    return {
        "unsafe_act": counts.get("unsafe_act", 0),
        "unsafe_behaviour": counts.get("unsafe_behaviour", 0),
        "unsafe_condition": counts.get("unsafe_condition", 0),
        "near_miss": len(near),
        "incident": len(incidents),
    }


@router.get("/activities")
def activities(
    session: SessionDep, user: Person = Depends(require_scope(*STAFF))
) -> list[dict[str, Any]]:
    now = site_now(session)
    weights = load_weights(session)
    out = []
    for a in session.scalars(select(Activity).order_by(Activity.grade.desc(), Activity.name)):
        uabc = _uabc(session, a.id, now - timedelta(days=365))
        out.append(
            {
                "id": a.id,
                "code": a.code,
                "name": a.name,
                "grade": a.grade,
                "exposure_hours_week": a.exposure_hours_week,
                "severity": a.severity,
                "hazards": hazards_of(session, a.id),
                "swp_items": len(
                    session.scalars(select(SwpItem.id).where(SwpItem.activity_id == a.id)).all()
                ),
                "uabc_total_12m": sum(uabc.values()),
                "control": control(session, a.id, now, weights).value,
            }
        )
    return out


@router.get("/activities/{activity_id}")
def activity(
    activity_id: int, session: SessionDep, user: Person = Depends(require_scope(*STAFF))
) -> dict[str, Any]:
    a = session.get(Activity, activity_id)
    if a is None:
        raise not_found("activity")
    now = site_now(session)
    weights = load_weights(session)
    hazards = hazards_of(session, a.id)
    hazard_names = {h.code: h.name for h in session.scalars(select(Hazard))}
    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"day": 0, "night": 0})
    for at, shift_kind in session.execute(
        select(Observation.at, Observation.shift_kind).where(
            Observation.activity_id == a.id,
            Observation.kind.in_(UABC_KINDS),
            Observation.at >= now - timedelta(days=365),
        )
    ):
        monthly[f"{at:%Y-%m}"][shift_kind.value] += 1
    alternative = (
        session.get(Activity, a.lower_hazard_alternative_id)
        if a.lower_hazard_alternative_id
        else None
    )
    control_layer = control(session, a.id, now, weights)
    return {
        "id": a.id,
        "code": a.code,
        "name": a.name,
        "grade": a.grade,
        "severity": a.severity,
        "exposure_hours_week": a.exposure_hours_week,
        "thresholds": list(weights.thresholds.get(a.grade, ())) or None,
        "hazards": [{"code": h, "name": hazard_names[h]} for h in hazards],
        "swp": [
            {"seq": s.seq, "text": s.text}
            for s in session.scalars(
                select(SwpItem).where(SwpItem.activity_id == a.id).order_by(SwpItem.seq)
            )
        ],
        "uabc_12m": _uabc(session, a.id, now - timedelta(days=365)),
        "uabc_by_month": [{"month": m, **v} for m, v in sorted(monthly.items())],
        "control": control_layer.value,
        "control_reason": control_layer.drivers[0]["reason"],
        "sensitivity": {
            d: max((weights.sens[h][d] for h in hazards), key="LMH".index)
            for d in weights.dimensions
        },
        "lower_hazard_alternative": alternative.name if alternative else None,
    }


@router.get("/groups")
def groups(
    session: SessionDep, user: Person = Depends(require_scope(*STAFF))
) -> list[dict[str, Any]]:
    rates = group_rates(session, site_now(session))
    defs = {g.code: g for g in GROUPS}
    return [
        {
            "code": code,
            "name": rate.name,
            "defined_by": defs[code].defined_by,
            "proposal": defs[code].proposal,
            "people": rate.people,
            "cards": rate.cards,
            "unsafe_per_100_cards": rate.unsafe_per_100_cards,
            "multiplier": round(rate.multiplier, 2),
            "assessed": rate.assessed,
        }
        for code, rate in rates.items()
    ]
