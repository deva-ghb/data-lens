"""Database engine, session factory and the declarative base.

Time convention: every datetime column stores naive UTC.
Columns typed `Mapped[datetime]` use `UtcDateTime`, which converts a timezone-aware
value to UTC and drops the offset before writing, and leaves a naive value as is
(a naive value is taken to be UTC already). Values read back are naive UTC.
The site is in the Gulf (UTC+4); converting to local time is a display concern.
The site clock (`SiteClock.now`) follows the same rule.

SQLite paths: a relative path in DATABASE_URL (the default is `data/datalens.db`) is
resolved against the backend/ directory, never the current working directory, so
running from another folder cannot create a second database.
"""

import enum
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Enum, MetaData, create_engine, event
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Stable constraint names, so later SQLite batch migrations can find and alter them.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UtcDateTime(TypeDecorator[datetime]):
    """A DateTime stored as naive UTC. Aware values are converted to UTC first."""

    impl = DateTime(timezone=False)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value


def _enum_values(enum_class: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_class]


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Every Python Enum used in a `Mapped[...]` annotation is stored as its plain string
    # value in a VARCHAR column and validated in Python (unknown strings raise on write).
    type_annotation_map = {
        datetime: UtcDateTime(),
        date: Date(),
        dict[str, Any]: JSON(),
        list[Any]: JSON(),
        enum.Enum: Enum(
            enum.Enum,
            native_enum=False,
            create_constraint=False,
            length=32,
            validate_strings=True,
            values_callable=_enum_values,
        ),
    }


def resolve_database_url(database_url: str) -> URL:
    """Anchor a relative SQLite file path to the backend/ directory."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return url
    database = url.database
    if not database or database == ":memory:" or database.startswith("file:"):
        return url
    path = Path(database)
    if path.is_absolute():
        return url
    return url.set(database=str(BACKEND_DIR / path))


def make_engine(database_url: str) -> Engine:
    url = resolve_database_url(database_url)
    is_sqlite = url.get_backend_name() == "sqlite"
    if is_sqlite and url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url)
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
