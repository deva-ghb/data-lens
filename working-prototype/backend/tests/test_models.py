from datetime import UTC, datetime, timedelta, timezone

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import delete, inspect, text, update
from sqlalchemy.exc import IntegrityError, StatementError

from app import db
from app.db import Base, make_engine
from app.migrate import alembic_config, upgrade_to_head
from app.models import (
    AuditEntry,
    AuditEntryImmutableError,
    Employer,
    EmployerKind,
    Person,
    SiteClock,
)

EXPECTED_TABLES = {
    # org
    "employers",
    "zones",
    "clinics",
    # people
    "people",
    "competencies",
    "person_competencies",
    "training_records",
    # activities
    "activities",
    "hazards",
    "activity_hazards",
    "swp_items",
    # roster
    "shifts",
    "gangs",
    "assignments",
    "check_ins",
    "absences",
    # feeds
    "feeds",
    "feed_readings",
    "clinic_visits",
    "camp_tickets",
    "lab_panels",
    # records
    "observations",
    "near_misses",
    "incidents",
    "hazard_reports",
    # warnings
    "warning_records",
    "warning_steps",
    # permits
    "permits",
    "permit_conditions",
    "permit_events",
    # actions
    "actions",
    "inspections",
    "inspection_checks",
    # learning
    "learning_items",
    "learning_reads",
    # health
    "fitness_outcomes",
    "unwell_events",
    # governance
    "site_clocks",
    "settings",
    "weights_versions",
    "audit_entries",
    # ai
    "ai_drafts",
    "ai_images",
    # engine outputs
    "score_runs",
    "assignment_scores",
    "swap_proposals",
    "contests",
}

PROTECTED_WORDS = ("nationality", "religion", "ethnicity", "origin")


def _audit_entry(**overrides) -> AuditEntry:
    values = {
        "at": datetime(2026, 7, 28, 18, 0),
        "actor_id": None,
        "actor_role": None,
        "action": "test.created",
        "subject_kind": "test",
        "subject_ref": "1",
    }
    values.update(overrides)
    return AuditEntry(**values)


def test_people_has_no_protected_columns():
    column_names = [column.name for column in Person.__table__.columns]
    for name in column_names:
        for word in PROTECTED_WORDS:
            assert word not in name, f"people.{name} looks like a protected attribute"


def test_tables_created_from_migration(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    upgrade_to_head(url)
    engine = make_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert tables - {"alembic_version"} == EXPECTED_TABLES
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_migration_matches_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'drift.db'}"
    upgrade_to_head(url)
    engine = make_engine(url)
    try:
        with engine.connect() as connection:
            diffs = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    assert diffs == []


def test_migration_leaves_foreign_keys_enforced(tmp_path):
    url = f"sqlite:///{tmp_path / 'fk.db'}"
    upgrade_to_head(url)
    engine = make_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    finally:
        engine.dispose()


def test_migration_downgrades_to_empty_and_upgrades_again(tmp_path):
    url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    upgrade_to_head(url)
    command.downgrade(alembic_config(url), "base")
    engine = make_engine(url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == {"alembic_version"}
        with engine.connect() as connection:
            triggers = connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            ).all()
            assert triggers == []
    finally:
        engine.dispose()
    upgrade_to_head(url)


def test_audit_entry_cannot_be_updated(session):
    entry = _audit_entry()
    session.add(entry)
    session.commit()

    entry.action = "test.rewritten"
    with pytest.raises(AuditEntryImmutableError):
        session.commit()


def test_audit_entry_cannot_be_deleted(session):
    entry = _audit_entry()
    session.add(entry)
    session.commit()

    session.delete(entry)
    with pytest.raises(AuditEntryImmutableError):
        session.commit()


def test_audit_entry_bulk_update_and_delete_are_blocked(session):
    session.add(_audit_entry())
    session.commit()

    with pytest.raises(AuditEntryImmutableError):
        session.execute(update(AuditEntry).values(action="test.rewritten"))
    session.rollback()
    with pytest.raises(AuditEntryImmutableError):
        session.execute(delete(AuditEntry))


def test_audit_entry_raw_sql_update_and_delete_are_blocked_by_the_database(session):
    session.add(_audit_entry())
    session.commit()

    with pytest.raises(IntegrityError):
        session.execute(text("UPDATE audit_entries SET action = 'x'"))
    session.rollback()
    with pytest.raises(IntegrityError):
        session.execute(text("DELETE FROM audit_entries"))
    session.rollback()
    assert session.execute(text("SELECT count(*) FROM audit_entries")).scalar() == 1


def test_audit_entry_can_still_be_appended(session):
    session.add(_audit_entry(action="first"))
    session.add(_audit_entry(action="second"))
    session.commit()
    assert session.execute(text("SELECT count(*) FROM audit_entries")).scalar() == 2


def test_enum_columns_store_plain_strings_and_reject_unknown_values(session):
    session.add(Employer(name="Mirsal Terminals", kind=EmployerKind.IN_HOUSE, logo_key="mirsal"))
    session.commit()
    stored = session.execute(text("SELECT kind FROM employers")).scalar()
    assert stored == "in_house"

    session.add(Employer(name="Unknown Co", kind="partner", logo_key="unknown"))
    with pytest.raises(StatementError):
        session.commit()


def test_aware_datetimes_are_stored_as_naive_utc(session):
    gulf = timezone(timedelta(hours=4))
    session.add(SiteClock(id=1, now=datetime(2026, 7, 28, 22, 0, tzinfo=gulf)))
    session.commit()
    session.expire_all()
    clock = session.get(SiteClock, 1)
    assert clock.now == datetime(2026, 7, 28, 18, 0)
    assert clock.now.tzinfo is None


def test_naive_datetimes_are_stored_unchanged(session):
    moment = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    session.add(SiteClock(id=1, now=moment))
    session.commit()
    session.expire_all()
    assert session.get(SiteClock, 1).now == moment


def test_site_clock_is_a_single_row(session):
    session.add(SiteClock(id=2, now=datetime(2026, 7, 28, 18, 0)))
    with pytest.raises(IntegrityError):
        session.commit()


def test_every_test_runs_on_a_fresh_temporary_database(session):
    committed = db.BACKEND_DIR / "data" / "datalens.db"
    assert db.engine.url.database != str(committed)
    assert session.execute(text("SELECT count(*) FROM employers")).scalar() == 0


def _migrated_engine(tmp_path, name):
    url = f"sqlite:///{tmp_path / name}"
    upgrade_to_head(url)
    return make_engine(url)


def test_audit_log_triggers_exist_at_migration_head(tmp_path):
    engine = _migrated_engine(tmp_path, "triggers.db")
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger'")
            ).all()
    finally:
        engine.dispose()
    assert {(row[0], row[1]) for row in rows} == {
        ("audit_entries_no_update", "audit_entries"),
        ("audit_entries_no_delete", "audit_entries"),
    }


@pytest.mark.parametrize(
    ("table", "columns"),
    [
        ("feed_readings", ["feed_id", "zone_id", "at"]),
        ("observations", ["activity_id", "at"]),
        ("clinic_visits", ["zone_id", "at"]),
    ],
)
def test_composite_indexes_exist_at_migration_head(tmp_path, table, columns):
    engine = _migrated_engine(tmp_path, f"{table}.db")
    try:
        indexes = inspect(engine).get_indexes(table)
    finally:
        engine.dispose()
    assert columns in [index["column_names"] for index in indexes]


def test_assignment_is_unique_per_shift_and_person(tmp_path):
    engine = _migrated_engine(tmp_path, "assignments.db")
    try:
        uniques = inspect(engine).get_unique_constraints("assignments")
    finally:
        engine.dispose()
    assert ["shift_id", "person_id"] in [constraint["column_names"] for constraint in uniques]
