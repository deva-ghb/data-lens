"""Permits to work, their conditions and event log."""

import enum
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PermitStatus(enum.StrEnum):
    REQUESTED = "requested"
    ASSESSED = "assessed"
    ISSUED = "issued"
    LIVE = "live"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class ConditionOrigin(enum.StrEnum):
    ISSUER = "issuer"
    WARNING = "warning"


class ConditionStatus(enum.StrEnum):
    DRAFT = "draft"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class Permit(Base):
    __tablename__ = "permits"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"), index=True)
    status: Mapped[PermitStatus] = mapped_column(default=PermitStatus.REQUESTED, index=True)
    # Null until an issuer takes the permit.
    issuer_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)


class PermitCondition(Base):
    __tablename__ = "permit_conditions"

    id: Mapped[int] = mapped_column(primary_key=True)
    permit_id: Mapped[int] = mapped_column(ForeignKey("permits.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    origin: Mapped[ConditionOrigin]
    # Set when the condition came from an early warning.
    warning_id: Mapped[int | None] = mapped_column(ForeignKey("warning_records.id"), index=True)
    status: Mapped[ConditionStatus] = mapped_column(default=ConditionStatus.DRAFT)


class PermitEvent(Base):
    __tablename__ = "permit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    permit_id: Mapped[int] = mapped_column(ForeignKey("permits.id"), index=True)
    at: Mapped[datetime]
    kind: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    # Null for events raised by the system, such as a sensor reading.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
