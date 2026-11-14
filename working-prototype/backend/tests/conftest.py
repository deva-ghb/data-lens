"""Shared test setup: every test runs against its own fresh, migrated SQLite file.

Tests must never touch the committed database at backend/data/datalens.db.
Before any app module is imported, DATABASE_URL is pointed at a throwaway file,
so even the engine built at import time lives in a temporary directory.
Then, for each test, a copy of a once-migrated template database is bound to
`app.db.engine` and `app.db.SessionLocal`.
"""

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

_IMPORT_GUARD_DIR = Path(tempfile.mkdtemp(prefix="datalens-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_IMPORT_GUARD_DIR / 'import-guard.db'}"

import pytest  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import db  # noqa: E402
from app.migrate import upgrade_to_head  # noqa: E402


@pytest.fixture(scope="session")
def migrated_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("template") / "template.db"
    upgrade_to_head(f"sqlite:///{path}")
    return path


@pytest.fixture(autouse=True)
def fresh_database(
    migrated_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Engine]:
    path = tmp_path / "test.db"
    shutil.copyfile(migrated_template, path)
    engine = db.make_engine(f"sqlite:///{path}")
    previous_bind = db.SessionLocal.kw.get("bind")
    monkeypatch.setattr(db, "engine", engine)
    db.SessionLocal.configure(bind=engine)
    try:
        yield engine
    finally:
        db.SessionLocal.configure(bind=previous_bind)
        engine.dispose()


@pytest.fixture
def session(fresh_database: Engine) -> Iterator[Session]:
    with db.SessionLocal() as session:
        yield session


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    shutil.rmtree(_IMPORT_GUARD_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def scenario_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The full seeded scenario, built once per test session."""
    from seed.build import build_database

    path = tmp_path_factory.mktemp("scenario") / "scenario.db"
    build_database(path)
    return path


@pytest.fixture
def scenario(scenario_template: Path, tmp_path: Path) -> Iterator[Session]:
    """A session on a private copy of the seeded scenario."""
    path = tmp_path / "scenario.db"
    shutil.copyfile(scenario_template, path)
    engine = db.make_engine(f"sqlite:///{path}")
    with Session(engine) as session:
        yield session
    engine.dispose()


class ApiClient:
    """A TestClient on a private copy of the scenario, signed in as one person."""

    def __init__(self) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        self._factory = lambda: TestClient(app)

    def as_user(self, email_local: str):  # type: ignore[no-untyped-def]
        client = self._factory()
        response = client.post(
            "/api/auth/login",
            json={"email": f"{email_local}@mirsalterminals.com", "password": "welcome@123"},
        )
        assert response.status_code == 200, response.text
        return client


@pytest.fixture
def api(
    scenario_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[ApiClient]:
    """The real app bound to a private copy of the seeded scenario."""
    path = tmp_path / "api.db"
    shutil.copyfile(scenario_template, path)
    engine = db.make_engine(f"sqlite:///{path}")
    previous_bind = db.SessionLocal.kw.get("bind")
    monkeypatch.setattr(db, "engine", engine)
    db.SessionLocal.configure(bind=engine)
    try:
        yield ApiClient()
    finally:
        db.SessionLocal.configure(bind=previous_bind)
        engine.dispose()
