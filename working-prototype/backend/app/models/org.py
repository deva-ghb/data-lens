"""Organisations, places and the clinic."""

import enum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EmployerKind(enum.StrEnum):
    IN_HOUSE = "in_house"
    CONTRACTOR = "contractor"


class ZoneKind(enum.StrEnum):
    BERTH = "berth"
    YARD_BLOCK = "yard_block"
    CAMP_BLOCK = "camp_block"
    DISTRICT = "district"


class Employer(Base):
    __tablename__ = "employers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[EmployerKind]
    # Names the drawn SVG logo the frontend renders for this organisation.
    logo_key: Mapped[str] = mapped_column(String(64))


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[ZoneKind]
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"), index=True)


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
