"""People, their competencies and training.

The people table deliberately has no nationality, religion, ethnicity or origin
columns. No model input or group definition may use them, so they are not stored.
"""

import enum
from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Role(enum.StrEnum):
    WORKER = "worker"
    FOREMAN = "foreman"
    PLANNER = "planner"
    SHIFT_MANAGER = "shift_manager"
    PERMIT_ISSUER = "permit_issuer"
    HSE_HEAD = "hse_head"
    CLINICIAN = "clinician"
    AUTHORITY = "authority"
    ADMIN = "admin"


class InductionPathway(enum.StrEnum):
    SITE = "site"
    CONTRACTOR = "contractor"


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    # Stored lower case; login compares lower case.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    role: Mapped[Role] = mapped_column(index=True)
    job_title: Mapped[str] = mapped_column(String(120))
    hire_date: Mapped[date]
    site_arrival_date: Mapped[date]
    induction: Mapped[InductionPathway]
    # Null for people who do not live in the workers' village.
    camp_zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), index=True)
    # Display preference only (a language code such as "en"); never a model input.
    display_language: Mapped[str] = mapped_column(String(16), default="en")
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(default=True)


class Competency(Base):
    __tablename__ = "competencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))


class PersonCompetency(Base):
    __tablename__ = "person_competencies"

    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), primary_key=True)
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("competencies.id"), primary_key=True, index=True
    )
    # Null when the competency does not expire.
    valid_until: Mapped[date | None]


class TrainingRecord(Base):
    __tablename__ = "training_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    course_code: Mapped[str] = mapped_column(String(40))
    completed_on: Mapped[date]
