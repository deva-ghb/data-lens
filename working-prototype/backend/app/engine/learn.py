"""Closing the loop on the weights: closed outcomes propose a new version; a person approves.

Nothing moves silently. A proposal is a new `WeightsVersion` with status "proposed" and a
note saying what changed and why. The engine keeps using the active version until a
person approves the proposal, and the approval is audited.
"""

import copy
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import audit
from app.clock import site_now
from app.models import Person, WarningRecord, WeightsVersion
from app.models.governance import WeightsStatus
from app.models.warnings import WarningOutcome, WarningStatus

THRESHOLD_STEP = 0.05
MIN_OUTCOMES = 3


def propose_weights_from_outcomes(session: Session) -> WeightsVersion | None:
    now = site_now(session)
    outcomes = list(
        session.scalars(
            select(WarningRecord.outcome).where(
                WarningRecord.status == WarningStatus.CLOSED,
                WarningRecord.outcome.is_not(None),
                WarningRecord.closed_at >= now - timedelta(days=90),
            )
        )
    )
    if len(outcomes) < MIN_OUTCOMES:
        return None
    false_alarms = sum(1 for o in outcomes if o == WarningOutcome.FALSE_ALARM)
    missed = sum(1 for o in outcomes if o == WarningOutcome.MISSED)
    if false_alarms / len(outcomes) > 0.4:
        step, why = THRESHOLD_STEP, f"{false_alarms} of {len(outcomes)} warnings were false alarms"
    elif missed:
        step, why = -THRESHOLD_STEP, f"{missed} of {len(outcomes)} events were missed"
    else:
        return None
    active = session.scalars(
        select(WeightsVersion).where(WeightsVersion.status == WeightsStatus.ACTIVE)
    ).one()
    body = copy.deepcopy(active.body_json)
    body["thresholds"] = {
        grade: [round(low + step, 2), round(high + step, 2)]
        for grade, (low, high) in body["thresholds"].items()
    }
    count = session.scalar(select(func.count()).select_from(WeightsVersion)) or 0
    version = f"v{count}"
    body["version"] = version
    direction = "Raise" if step > 0 else "Lower"
    body["note"] = f"{direction} every tier threshold by {abs(step):.2f}: {why} in 90 days."
    pending = session.scalars(
        select(WeightsVersion).where(WeightsVersion.status == WeightsStatus.PROPOSED)
    ).all()
    for existing in pending:
        if existing.body_json.get("thresholds") == body["thresholds"]:
            return existing  # the same change is already waiting for a person
    proposal = WeightsVersion(version=version, status=WeightsStatus.PROPOSED, body_json=body)
    session.add(proposal)
    session.flush()
    audit(
        session,
        None,
        "weights_proposed",
        "weights",
        version,
        evidence={"from": active.version, "change": body["note"]},
    )
    return proposal


def approve_weights(session: Session, version_id: int, actor: Person | None) -> WeightsVersion:
    proposal = session.get(WeightsVersion, version_id)
    if proposal is None:
        raise LookupError("That weights version does not exist.")
    if proposal.status != WeightsStatus.PROPOSED:
        raise ValueError("Only a proposed weights version can be approved.")
    # A proposal is a change to the version that was active when it was made. Any other
    # proposals still pending are stale once this one is approved.
    for stale in session.scalars(
        select(WeightsVersion).where(
            WeightsVersion.status == WeightsStatus.PROPOSED, WeightsVersion.id != proposal.id
        )
    ):
        stale.status = WeightsStatus.RETIRED
    for active in session.scalars(
        select(WeightsVersion).where(WeightsVersion.status == WeightsStatus.ACTIVE)
    ):
        active.status = WeightsStatus.RETIRED
    session.flush()
    proposal.status = WeightsStatus.ACTIVE
    proposal.approved_by = actor.id if actor else None
    proposal.approved_at = site_now(session)
    session.flush()
    audit(session, actor, "weights_approved", "weights", proposal.version)
    return proposal
