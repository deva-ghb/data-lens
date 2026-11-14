"""Site clock, settings, versioned weights and the append-only audit log.

Audit entries can be added but never changed or removed. Three layers enforce this:
- a `before_flush` listener rejects any modified or deleted AuditEntry in a session;
- a `do_orm_execute` listener rejects bulk `update(AuditEntry)` and `delete(AuditEntry)`;
- database triggers (created by the migration) abort any UPDATE or DELETE on
  audit_entries, which also covers raw SQL.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, event, text
from sqlalchemy.orm import Mapped, ORMExecuteState, Session, mapped_column

from app.db import Base
from app.models.people import Role


class WeightsStatus(enum.StrEnum):
    ACTIVE = "active"
    PROPOSED = "proposed"
    RETIRED = "retired"


class SiteClock(Base):
    """The single row holding the site's current time (naive UTC)."""

    __tablename__ = "site_clocks"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    now: Mapped[datetime]


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Any JSON value: a number such as the small-cell threshold, or a structured object.
    value: Mapped[Any] = mapped_column(JSON)


class WeightsVersion(Base):
    __tablename__ = "weights_versions"
    __table_args__ = (
        # At most one active weights version at a time.
        Index(
            "uq_weights_versions_one_active",
            "status",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(16), unique=True)
    status: Mapped[WeightsStatus] = mapped_column(default=WeightsStatus.PROPOSED)
    body_json: Mapped[dict[str, Any]]
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    approved_at: Mapped[datetime | None]


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(index=True)
    # Null actor and role mean the system acted (for example a scheduled engine run).
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    actor_role: Mapped[Role | None]
    action: Mapped[str] = mapped_column(String(64))
    subject_kind: Mapped[str] = mapped_column(String(32))
    # A record id, or a per-shift token for reassignments so the worker is not named.
    subject_ref: Mapped[str] = mapped_column(String(128))
    evidence_json: Mapped[dict[str, Any] | None]
    model_version: Mapped[str | None] = mapped_column(String(64))


class AuditEntryImmutableError(Exception):
    """Raised when code tries to change or remove an audit entry."""


@event.listens_for(Session, "before_flush")
def _block_audit_changes(session: Session, _flush_context: Any, _instances: Any) -> None:
    for instance in session.deleted:
        if isinstance(instance, AuditEntry):
            raise AuditEntryImmutableError("Audit entries cannot be deleted.")
    for instance in session.dirty:
        if isinstance(instance, AuditEntry) and session.is_modified(instance):
            raise AuditEntryImmutableError("Audit entries cannot be changed.")


@event.listens_for(Session, "do_orm_execute")
def _block_bulk_audit_changes(state: ORMExecuteState) -> None:
    if not (state.is_update or state.is_delete):
        return
    if any(mapper.class_ is AuditEntry for mapper in state.all_mappers):
        raise AuditEntryImmutableError("Audit entries cannot be changed or deleted.")
