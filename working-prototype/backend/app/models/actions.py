"""Corrective actions and targeted inspections.

`source_kind` and `source_id` point at the record that raised the action or
inspection (for example an incident or a warning record). They are not foreign keys
because the source can be one of several tables.
"""

import enum
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ControlLevel(enum.StrEnum):
    ELIMINATE = "eliminate"
    SUBSTITUTE = "substitute"
    ENGINEER = "engineer"
    ADMINISTRATIVE = "administrative"
    PPE = "ppe"


class ActionStatus(enum.StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class InspectionStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    DONE = "done"
    CANCELLED = "cancelled"


class CheckResult(enum.StrEnum):
    CONFIRMED = "confirmed"
    NOT_FOUND = "not_found"


class Action(Base):
    __tablename__ = "actions"
    __table_args__ = (Index(None, "source_kind", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_kind: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    control_level: Mapped[ControlLevel]
    owner_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    due_on: Mapped[date]
    status: Mapped[ActionStatus] = mapped_column(default=ActionStatus.OPEN)
    effectiveness_check_on: Mapped[date | None]
    # Null until the effectiveness check is done.
    effective: Mapped[bool | None]


class Inspection(Base):
    __tablename__ = "inspections"
    __table_args__ = (Index(None, "source_kind", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_kind: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int]
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    due_at: Mapped[datetime]
    status: Mapped[InspectionStatus] = mapped_column(default=InspectionStatus.SCHEDULED)


class InspectionCheck(Base):
    __tablename__ = "inspection_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), index=True)
    # The risk driver this check tests, for example "heat" or "camp_cooling".
    driver: Mapped[str] = mapped_column(String(64))
    question: Mapped[str] = mapped_column(Text)
    # Null until the inspector answers.
    result: Mapped[CheckResult | None]
    note: Mapped[str | None] = mapped_column(Text)
