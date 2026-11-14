from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import audit
from app.clock import current_shift, set_site_now, site_now
from app.models import AuditEntry, Employer, Person, Role, Setting, Shift
from app.models.org import EmployerKind
from app.models.people import InductionPathway
from app.models.roster import ShiftKind
from app.policy.access import ACCESS, DataScope, can
from app.policy.suppression import Cell, round_to_5, small_cell_threshold, suppress
from app.policy.tokens import shift_token


def _person(session: Session, role: Role, email: str) -> Person:
    employer = session.scalar(select(Employer)) or Employer(
        name="Mirsal Terminals", kind=EmployerKind.IN_HOUSE, logo_key="mirsal"
    )
    session.add(employer)
    session.flush()
    person = Person(
        employer_id=employer.id,
        first_name="Test",
        last_name=role.value,
        email=email,
        role=role,
        job_title="Tester",
        hire_date=date(2024, 1, 1),
        site_arrival_date=date(2024, 1, 1),
        induction=InductionPathway.SITE,
        password_hash="x",
    )
    session.add(person)
    session.flush()
    return person


def test_suppression_hides_cells_below_threshold() -> None:
    table = suppress([Cell("A", 12), Cell("B", 4), Cell("C", 30)], k=10)
    assert [c.value for c in table.cells] == [12, None, 30]
    assert table.suppressed_count == 1


def test_totals_rounded_so_hidden_cell_not_recoverable() -> None:
    table = suppress([Cell("A", 12), Cell("B", 4), Cell("C", 30)], k=10)
    assert table.total == 45
    visible = sum(c.value for c in table.cells if c.value is not None)
    assert table.total - visible != 4


def test_round_to_5() -> None:
    assert [round_to_5(n) for n in (0, 2, 3, 46, 47, 50)] == [0, 0, 5, 45, 45, 50]


def test_threshold_setting_is_read_from_settings_table(session: Session) -> None:
    assert small_cell_threshold(session) == 10
    session.add(Setting(key="small_cell_threshold", value=15))
    session.flush()
    assert small_cell_threshold(session) == 15


def test_reassignment_audit_uses_shift_token_not_person_id(session: Session) -> None:
    planner = _person(session, Role.PLANNER, "daniel.mensah@mirsalterminals.com")
    worker = _person(session, Role.WORKER, "arjun.thapa@mirsalterminals.com")
    token = shift_token(worker.id, 42)
    audit(session, planner, "swap_accepted", "reassignment", token, evidence={"shift_id": 42})
    entry = session.scalars(select(AuditEntry)).one()
    assert entry.subject_ref == token
    assert entry.subject_ref.startswith("st-")
    assert entry.subject_ref not in (str(worker.id), worker.email)
    assert entry.actor_role == Role.PLANNER
    assert shift_token(worker.id, 42) == token
    assert shift_token(worker.id, 43) != token


def test_planner_cannot_read_health_detail() -> None:
    assert not can(Role.PLANNER, "health_detail")
    assert can(Role.PLANNER, "site_tiers")
    assert can(Role.CLINICIAN, "health_detail")
    assert not can(Role.HSE_HEAD, "health_detail")
    assert can(Role.WORKER, "own_health")
    assert not can(Role.WORKER, "site_tiers")
    assert can(Role.FOREMAN, "crew_actions")
    assert not can(Role.FOREMAN, "site_tiers")
    assert can(Role.PERMIT_ISSUER, "permit_counts")
    assert not can(Role.PERMIT_ISSUER, "site_tiers")


def test_authority_reads_audit_redacted_only() -> None:
    assert can(Role.AUTHORITY, "audit_redacted")
    assert can(Role.AUTHORITY, "district_aggregates")
    assert can(Role.AUTHORITY, "employer_aggregates")
    assert not can(Role.AUTHORITY, "all_records")
    assert not can(Role.AUTHORITY, "aggregates")
    assert not can(Role.AUTHORITY, "health_detail")


def test_every_role_has_an_access_entry() -> None:
    assert set(ACCESS) == set(Role)
    scopes: set[DataScope] = set().union(*ACCESS.values())
    assert "admin" in scopes


def test_site_clock_set_and_read_is_audited(session: Session) -> None:
    admin = _person(session, Role.ADMIN, "hessa.almansoori@mirsalterminals.com")
    set_site_now(session, datetime(2026, 7, 28, 14, 0), admin)
    assert site_now(session) == datetime(2026, 7, 28, 14, 0)
    entry = session.scalars(select(AuditEntry)).one()
    assert entry.action == "site_clock_set"


def test_current_shift_contains_site_now(session: Session) -> None:
    admin = _person(session, Role.ADMIN, "hessa.almansoori@mirsalterminals.com")
    day = Shift(
        date=date(2026, 7, 29),
        kind=ShiftKind.DAY,
        start_at=datetime(2026, 7, 29, 3, 0),
        end_at=datetime(2026, 7, 29, 15, 0),
    )
    night = Shift(
        date=date(2026, 7, 29),
        kind=ShiftKind.NIGHT,
        start_at=datetime(2026, 7, 29, 15, 0),
        end_at=datetime(2026, 7, 30, 3, 0),
    )
    session.add_all([day, night])
    set_site_now(session, datetime(2026, 7, 29, 16, 0), admin)
    assert current_shift(session).id == night.id
    set_site_now(session, datetime(2026, 7, 29, 15, 0), admin)
    assert current_shift(session).id == night.id


def test_current_shift_without_any_shift_raises(session: Session) -> None:
    admin = _person(session, Role.ADMIN, "hessa.almansoori@mirsalterminals.com")
    set_site_now(session, datetime(2026, 7, 29, 16, 0), admin)
    with pytest.raises(LookupError):
        current_shift(session)
