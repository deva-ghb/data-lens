"""Occupational health outcomes and unwell reports."""

import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FitnessDecision(enum.StrEnum):
    FIT = "fit"
    FIT_WITH_RESTRICTIONS = "fit_with_restrictions"
    NOT_TODAY = "not_today"


class FitnessOutcome(Base):
    __tablename__ = "fitness_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    decided_by: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    at: Mapped[datetime]
    outcome: Mapped[FitnessDecision]
    restriction_text: Mapped[str | None] = mapped_column(Text)
    # When false, the employer sees "outcome not shared" and the engine treats the
    # person as unknown, not fit, for graded work.
    share_with_employer: Mapped[bool] = mapped_column(default=False)


class UnwellEvent(Base):
    __tablename__ = "unwell_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"), index=True)
    at: Mapped[datetime]
    # The live permit the person was working under, when there was one.
    permit_id: Mapped[int | None] = mapped_column(ForeignKey("permits.id"), index=True)
