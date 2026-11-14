"""Corrective and preventive actions, and learning items with read counts."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.ai.drafts import stored_draft
from app.api.common import (
    SessionDep,
    UserDep,
    conflict,
    draft_out,
    not_found,
    person_name,
    require_role,
    require_scope,
)
from app.audit import audit
from app.clock import site_now
from app.errors import ApiError
from app.models import (
    Action,
    AiDraft,
    Assignment,
    Gang,
    LearningItem,
    LearningRead,
    Person,
    WarningRecord,
    WarningStep,
)
from app.models.actions import ActionStatus, ControlLevel
from app.models.learning import LearningStatus
from app.models.warnings import WarningOutcome, WarningStatus, WarningStepStatus
from app.policy.suppression import Cell, small_cell_threshold, suppress

router = APIRouter(tags=["actions"])
HIERARCHY = [
    ControlLevel.ELIMINATE,
    ControlLevel.SUBSTITUTE,
    ControlLevel.ENGINEER,
    ControlLevel.ADMINISTRATIVE,
    ControlLevel.PPE,
]


def _out(session, a: Action) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "id": a.id,
        "title": a.title,
        "control_level": a.control_level.value,
        "owner": person_name(session, a.owner_id),
        "owner_id": a.owner_id,
        "due_on": a.due_on.isoformat(),
        "status": a.status.value,
        "effectiveness_check_on": a.effectiveness_check_on.isoformat()
        if a.effectiveness_check_on
        else None,
        "effective": a.effective,
        "source_kind": a.source_kind,
        "source_id": a.source_id,
    }


@router.get("/actions")
def actions(
    session: SessionDep,
    user: Person = Depends(require_scope("aggregates", "crew_actions", "site_tiers")),
) -> list[dict[str, Any]]:
    rows = session.scalars(select(Action)).all()
    rows = sorted(rows, key=lambda a: (HIERARCHY.index(a.control_level), a.due_on))
    return [_out(session, a) for a in rows]


class ActionBody(BaseModel):
    source_kind: str
    source_id: int
    title: str
    control_level: str
    owner_id: int | None = None
    due_on: date | None = None
    effectiveness_check_on: date | None = None


@router.post("/actions", status_code=201)
def create(
    body: ActionBody, session: SessionDep, user: Person = Depends(require_role("hse_head"))
) -> dict[str, Any]:
    if (
        not body.title.strip()
        or body.owner_id is None
        or body.due_on is None
        or body.effectiveness_check_on is None
    ):
        raise ApiError(
            422,
            "invalid_input",
            "An action needs a title, an owner, a due date and an effectiveness check date.",
        )
    if session.get(Person, body.owner_id) is None:
        raise not_found("owner")
    try:
        level = ControlLevel(body.control_level)
    except ValueError:
        raise ApiError(
            422, "invalid_input", "Choose a level from the hierarchy of controls."
        ) from None
    action = Action(
        source_kind=body.source_kind,
        source_id=body.source_id,
        title=body.title.strip(),
        control_level=level,
        owner_id=body.owner_id,
        due_on=body.due_on,
        status=ActionStatus.OPEN,
        effectiveness_check_on=body.effectiveness_check_on,
        effective=None,
    )
    session.add(action)
    session.flush()
    audit(
        session,
        user,
        "action_created",
        body.source_kind,
        str(body.source_id),
        evidence={"action": action.id},
    )
    session.commit()
    return _out(session, action)


class ActionPatch(BaseModel):
    status: str | None = None
    effective: bool | None = None


@router.patch("/actions/{action_id}")
def update(action_id: int, body: ActionPatch, session: SessionDep, user: UserDep) -> dict[str, Any]:
    a = session.get(Action, action_id)
    if a is None:
        raise not_found("action")
    if user.id != a.owner_id and user.role.value not in ("hse_head",):
        raise ApiError(403, "forbidden", "Only the owner or the HSE head can update this action.")
    if body.status:
        try:
            a.status = ActionStatus(body.status)
        except ValueError:
            raise ApiError(422, "invalid_input", "Unknown action status.") from None
    if body.effective is not None:
        today = site_now(session).date()
        if a.effectiveness_check_on and today < a.effectiveness_check_on:
            raise conflict(f"The effectiveness check is due on {a.effectiveness_check_on:%d %B}.")
        if a.status != ActionStatus.DONE:
            raise conflict("Mark the action done before checking that it worked.")
        a.effective = body.effective
        _maybe_close_warning(session, a)
    audit(
        session,
        user,
        "action_updated",
        a.source_kind,
        str(a.source_id),
        evidence={"action": a.id, "status": a.status.value, "effective": a.effective},
    )
    session.commit()
    return _out(session, a)


def _maybe_close_warning(session, a: Action) -> None:  # type: ignore[no-untyped-def]
    """Step 10 closes automatically at the effectiveness check, once every action worked."""
    if a.source_kind != "warning":
        return
    w = session.get(WarningRecord, a.source_id)
    if w is None or w.status != WarningStatus.OPEN:
        return
    linked = session.scalars(
        select(Action).where(Action.source_kind == "warning", Action.source_id == w.id)
    ).all()
    if all(x.effective for x in linked):
        w.status = WarningStatus.CLOSED
        w.outcome = WarningOutcome.RIGHT
        w.closed_at = site_now(session)
        step = session.scalars(
            select(WarningStep).where(WarningStep.warning_id == w.id, WarningStep.step == 10)
        ).one()
        step.status = WarningStepStatus.CONFIRMED
        step.confirmed_at = w.closed_at


# --- learning -----------------------------------------------------------------------------


def _item_out(session, item: LearningItem, with_reads: bool, k: int) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    draft = session.get(AiDraft, item.draft_id) if item.draft_id else None
    out: dict[str, Any] = {
        "id": item.id,
        "kind": item.kind.value,
        "status": item.status.value,
        "source_kind": item.source_kind,
        "source_id": item.source_id,
        "content": draft.content if draft else "",
        "reads": session.scalar(
            select(func.count()).select_from(LearningRead).where(LearningRead.item_id == item.id)
        ),
    }
    if with_reads:
        by_gang: dict[str, int] = {}
        for gang_name, n in session.execute(
            select(Gang.name, func.count(func.distinct(LearningRead.person_id)))
            .join(Assignment, Assignment.person_id == LearningRead.person_id)
            .join(Gang, Gang.id == Assignment.gang_id)
            .where(LearningRead.item_id == item.id)
            .group_by(Gang.name)
        ):
            by_gang[gang_name] = n
        table = suppress([Cell(g, n) for g, n in sorted(by_gang.items())], k)
        out["reads_by_crew"] = [{"crew": c.label, "reads": c.value} for c in table.cells]
    return out


@router.get("/learning")
def learning(
    session: SessionDep, user: Person = Depends(require_scope("aggregates", "crew_actions"))
) -> dict[str, Any]:
    k = small_cell_threshold(session)
    items = session.scalars(select(LearningItem).order_by(LearningItem.id.desc())).all()
    return {"threshold": k, "items": [_item_out(session, i, True, k) for i in items]}


@router.get("/learning/mine")
def my_cards(session: SessionDep, user: UserDep) -> list[dict[str, Any]]:
    items = session.scalars(
        select(LearningItem).where(
            LearningItem.status == LearningStatus.PUBLISHED, LearningItem.kind == "card"
        )
    ).all()
    read = set(
        session.scalars(select(LearningRead.item_id).where(LearningRead.person_id == user.id))
    )
    return [{**_item_out(session, i, False, 0), "read": i.id in read} for i in items]


@router.post("/learning/{item_id}/read")
def mark_read(item_id: int, session: SessionDep, user: UserDep) -> dict[str, Any]:
    if session.get(LearningItem, item_id) is None:
        raise not_found("card")
    if session.get(LearningRead, (item_id, user.id)) is None:
        session.add(LearningRead(item_id=item_id, person_id=user.id, at=site_now(session)))
        session.commit()
    return {"id": item_id, "read": True}


__all__ = ["router", "draft_out", "stored_draft"]


@router.post("/learning/{item_id}/publish")
def publish(
    item_id: int, session: SessionDep, user: Person = Depends(require_role("hse_head"))
) -> dict[str, Any]:
    item = session.get(LearningItem, item_id)
    if item is None:
        raise not_found("learning item")
    if item.status == LearningStatus.PUBLISHED:
        raise conflict("Already shared.")
    item.status = LearningStatus.PUBLISHED
    audit(session, user, "learning_shared", "learning", str(item.id))
    session.commit()
    return {"id": item.id, "status": item.status.value}
