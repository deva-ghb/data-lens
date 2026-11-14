"""Early warning records and their ten confirmed steps."""

import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WarningLevel(enum.StrEnum):
    WATCH = "watch"
    WARNING = "warning"
    ALERT = "alert"


class WarningStatus(enum.StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class WarningOutcome(enum.StrEnum):
    RIGHT = "right"
    EARLY = "early"
    FALSE_ALARM = "false_alarm"
    MISSED = "missed"


class WarningStepStatus(enum.StrEnum):
    PENDING = "pending"
    DRAFTED = "drafted"
    CONFIRMED = "confirmed"


class WarningRecord(Base):
    __tablename__ = "warning_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    opened_at: Mapped[datetime] = mapped_column(index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    level: Mapped[WarningLevel]
    status: Mapped[WarningStatus] = mapped_column(default=WarningStatus.OPEN)
    # Null until the warning is closed and judged.
    outcome: Mapped[WarningOutcome | None]
    closed_at: Mapped[datetime | None]


class WarningStep(Base):
    __tablename__ = "warning_steps"
    __table_args__ = (
        UniqueConstraint("warning_id", "step"),
        CheckConstraint("step BETWEEN 1 AND 10", name="step_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    warning_id: Mapped[int] = mapped_column(ForeignKey("warning_records.id"))
    step: Mapped[int]
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("ai_drafts.id"), index=True)
    status: Mapped[WarningStepStatus] = mapped_column(default=WarningStepStatus.PENDING)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    confirmed_at: Mapped[datetime | None]
