"""Engine outputs. These rows are computed and written by engine runs, never seeded."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RunKind(enum.StrEnum):
    EVENING = "evening"
    SHIFT_START = "shift_start"
    MANUAL = "manual"


class ConditionsSource(enum.StrEnum):
    SCENARIO = "scenario"
    LIVE = "live"


class Tier(enum.StrEnum):
    FIT = "fit"
    FIT_WITH_CONTROLS = "fit_with_controls"
    REASSIGN = "reassign"
    REFER = "refer"
    UNKNOWN = "unknown"


class SwapStatus(enum.StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContestStatus(enum.StrEnum):
    OPEN = "open"
    UPHELD = "upheld"
    DISMISSED = "dismissed"


class ScoreRun(Base):
    __tablename__ = "score_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[RunKind]
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"), index=True)
    weights_version_id: Mapped[int] = mapped_column(ForeignKey("weights_versions.id"), index=True)
    ran_at: Mapped[datetime]
    conditions_source: Mapped[ConditionsSource] = mapped_column(default=ConditionsSource.SCENARIO)


class AssignmentScore(Base):
    __tablename__ = "assignment_scores"
    __table_args__ = (UniqueConstraint("run_id", "assignment_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("score_runs.id"))
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), index=True)
    intrinsic: Mapped[float]
    control: Mapped[float]
    condition: Mapped[float]
    profile: Mapped[float]
    r: Mapped[float]
    tier: Mapped[Tier]
    drivers_json: Mapped[list[Any]]
    confidence: Mapped[float]
    group_step_limited: Mapped[bool] = mapped_column(default=False)


class SwapProposal(Base):
    __tablename__ = "swap_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("score_runs.id"), index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), index=True)
    to_activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), index=True)
    # The work the worker had when the swap was proposed, so history reads correctly after.
    from_activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id"), index=True)
    status: Mapped[SwapStatus] = mapped_column(default=SwapStatus.PROPOSED)
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)


class Contest(Base):
    __tablename__ = "contests"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_score_id: Mapped[int] = mapped_column(ForeignKey("assignment_scores.id"), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[ContestStatus] = mapped_column(default=ContestStatus.OPEN)
