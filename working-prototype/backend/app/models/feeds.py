"""Signal feeds and the raw records they bring in."""

import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SignalClass(enum.StrEnum):
    CLINICAL = "clinical"
    WORKPLACE = "workplace"
    ENVIRONMENTAL = "environmental"
    COMMUNITY = "community"
    WORKER_REPORTED = "worker_reported"


class FeedSource(enum.StrEnum):
    SEEDED = "seeded"
    LIVE = "live"
    UPLOADED = "uploaded"


class Feed(Base):
    __tablename__ = "feeds"
    __table_args__ = (
        CheckConstraint("cadence_minutes > 0", name="cadence_positive"),
        CheckConstraint("allowed_delay_minutes >= 0", name="allowed_delay_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    signal_class: Mapped[SignalClass]
    cadence_minutes: Mapped[int]
    allowed_delay_minutes: Mapped[int]
    # The finest place the feed reports at, for example "site", "berth" or "camp_block".
    location_level: Mapped[str] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column(default=True)
    source: Mapped[FeedSource]


class FeedReading(Base):
    __tablename__ = "feed_readings"
    __table_args__ = (Index(None, "feed_id", "at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"))
    # Null for site-wide readings.
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), index=True)
    at: Mapped[datetime]
    metric: Mapped[str] = mapped_column(String(40))
    value: Mapped[float]
    source: Mapped[FeedSource]


class ClinicVisit(Base):
    __tablename__ = "clinic_visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    at: Mapped[datetime] = mapped_column(index=True)
    syndrome: Mapped[str] = mapped_column(String(40))


class CampTicket(Base):
    __tablename__ = "camp_tickets"
    __table_args__ = (
        CheckConstraint(
            "units_affected >= 0 AND units_affected <= units_total", name="units_in_range"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    opened_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]
    kind: Mapped[str] = mapped_column(String(40))
    units_affected: Mapped[int]
    units_total: Mapped[int]


class LabPanel(Base):
    __tablename__ = "lab_panels"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    at: Mapped[datetime]
    panel: Mapped[str] = mapped_column(String(40))
    value: Mapped[float]
    # Null when the value is in range, otherwise for example "high" or "low".
    flag: Mapped[str | None] = mapped_column(String(16))
