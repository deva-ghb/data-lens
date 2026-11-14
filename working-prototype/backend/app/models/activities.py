"""Port activities, their hazards and safe work procedure (SWP) items."""

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("grade BETWEEN 1 AND 5", name="grade_range"),
        CheckConstraint("severity BETWEEN 1 AND 5", name="severity_range"),
        CheckConstraint("exposure_hours_week >= 0", name="exposure_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    grade: Mapped[int]
    exposure_hours_week: Mapped[float]
    severity: Mapped[int]
    # The competency a person must hold to be assigned; null when none is required.
    competency_id: Mapped[int | None] = mapped_column(ForeignKey("competencies.id"), index=True)
    lower_hazard_alternative_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id"), index=True
    )


class Hazard(Base):
    __tablename__ = "hazards"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))


class ActivityHazard(Base):
    __tablename__ = "activity_hazards"

    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), primary_key=True)
    hazard_id: Mapped[int] = mapped_column(ForeignKey("hazards.id"), primary_key=True, index=True)


class SwpItem(Base):
    __tablename__ = "swp_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), index=True)
    seq: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    # An SWP change retires an item rather than deleting it.
    active: Mapped[bool] = mapped_column(default=True)
