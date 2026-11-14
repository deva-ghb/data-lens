"""Safety records: observations, near misses, incidents and hazard reports."""

import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.roster import ShiftKind


class ObservationKind(enum.StrEnum):
    UNSAFE_ACT = "unsafe_act"
    UNSAFE_BEHAVIOUR = "unsafe_behaviour"
    UNSAFE_CONDITION = "unsafe_condition"
    SAFE = "safe"


class RecordStatus(enum.StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    CLOSED = "closed"


class IncidentKind(enum.StrEnum):
    INJURY = "injury"
    ILLNESS = "illness"
    PROPERTY = "property"
    ENVIRONMENT = "environment"


class Observation(Base):
    __tablename__ = "observations"
    # Serves "observations for an activity over a time window"; its first column also covers
    # activity-only lookups.
    __table_args__ = (Index(None, "activity_id", "at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"))
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    # The person observed, when the card names one.
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    at: Mapped[datetime] = mapped_column(index=True)
    kind: Mapped[ObservationKind]
    shift_kind: Mapped[ShiftKind]
    text: Mapped[str] = mapped_column(Text)


class NearMiss(Base):
    __tablename__ = "near_misses"
    __table_args__ = (
        CheckConstraint("potential_severity BETWEEN 1 AND 5", name="potential_severity_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    reported_by: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    at: Mapped[datetime] = mapped_column(index=True)
    shift_kind: Mapped[ShiftKind]
    text: Mapped[str] = mapped_column(Text)
    potential_severity: Mapped[int]
    status: Mapped[RecordStatus] = mapped_column(default=RecordStatus.OPEN)
    photo_key: Mapped[str | None] = mapped_column(String(255))


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("potential_severity BETWEEN 1 AND 5", name="potential_severity_range"),
        CheckConstraint("actual_severity BETWEEN 1 AND 5", name="actual_severity_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    reported_by: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    at: Mapped[datetime] = mapped_column(index=True)
    shift_kind: Mapped[ShiftKind]
    kind: Mapped[IncidentKind]
    text: Mapped[str] = mapped_column(Text)
    # Key of a stored photo, when one was attached.
    photo_key: Mapped[str | None] = mapped_column(String(255))
    potential_severity: Mapped[int]
    # Null until the outcome is known.
    actual_severity: Mapped[int | None]
    lost_time: Mapped[bool] = mapped_column(default=False)
    status: Mapped[RecordStatus] = mapped_column(default=RecordStatus.OPEN)
    closed_at: Mapped[datetime | None]


class HazardReport(Base):
    __tablename__ = "hazard_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    reported_by: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    at: Mapped[datetime] = mapped_column(index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[RecordStatus] = mapped_column(default=RecordStatus.OPEN)
    photo_key: Mapped[str | None] = mapped_column(String(255))
