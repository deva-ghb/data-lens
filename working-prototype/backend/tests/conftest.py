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
