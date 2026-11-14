"""Shifts, gangs, assignments, check-ins and absences."""

import enum
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ShiftKind(enum.StrEnum):
    DAY = "day"
    NIGHT = "night"


class AssignmentSource(enum.StrEnum):
    ROSTER = "roster"
    SWAP = "swap"


class Feeling(enum.StrEnum):
    GOOD = "good"
    TIRED = "tired"
    UNWELL = "unwell"


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (UniqueConstraint("date", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date]
    kind: Mapped[ShiftKind]
    start_at: Mapped[datetime]
    end_at: Mapped[datetime]


class Gang(Base):
    __tablename__ = "gangs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    foreman_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)


class Assignment(Base):
    """A person's place on one shift: one row per person per shift.

    A swap updates the existing row in place (new activity and gang) and sets
    `source` to "swap"; it never adds a second row for the same person and shift.
    """

    __tablename__ = "assignments"
    # The unique constraint also serves lookups by shift alone.
    __table_args__ = (UniqueConstraint("shift_id", "person_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), index=True)
    gang_id: Mapped[int | None] = mapped_column(ForeignKey("gangs.id"), index=True)
    # Where the work happens (a berth or yard block); null for site-wide work such as the gate.
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), index=True)
    source: Mapped[AssignmentSource] = mapped_column(default=AssignmentSource.ROSTER)


class CheckIn(Base):
    __tablename__ = "check_ins"
    __table_args__ = (UniqueConstraint("person_id", "shift_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"), index=True)
    at: Mapped[datetime]
    # A band label such as "under_5", "5_to_6", "6_to_7", "7_plus".
    sleep_hours_band: Mapped[str] = mapped_column(String(16))
    feeling: Mapped[Feeling]
    hydration_ok: Mapped[bool]


class Absence(Base):
    __tablename__ = "absences"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    date: Mapped[date]
    # For example "sickness" or "leave".
    kind: Mapped[str] = mapped_column(String(32))


class VesselCall(Base):
    """A vessel alongside a berth. Drives the pace of work on that berth's shifts."""

    __tablename__ = "vessel_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_name: Mapped[str] = mapped_column(String(80))
    berth_zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    arrives_at: Mapped[datetime] = mapped_column(index=True)
    departs_at: Mapped[datetime]
    moves_planned: Mapped[int]
