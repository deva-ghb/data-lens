from pathlib import Path

from sqlalchemy import text

from app import db
from app.db import BACKEND_DIR, get_session, resolve_database_url


def test_sqlite_foreign_keys_are_on():
    with db.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_get_session_yields_and_closes_a_session():
    generator = get_session()
    session = next(generator)
    assert session.execute(text("SELECT 1")).scalar() == 1
    generator.close()


def test_backend_dir_is_the_backend_folder():
    assert BACKEND_DIR == Path(__file__).resolve().parents[1]
    assert (BACKEND_DIR / "alembic.ini").is_file()


def test_relative_sqlite_path_is_anchored_to_backend_dir():
    url = resolve_database_url("sqlite:///data/datalens.db")
    assert url.database == str(BACKEND_DIR / "data" / "datalens.db")


def test_relative_sqlite_path_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    url = resolve_database_url("sqlite:///data/datalens.db")
    assert url.database == str(BACKEND_DIR / "data" / "datalens.db")


def test_absolute_sqlite_path_is_kept(tmp_path):
    target = tmp_path / "other.db"
    assert resolve_database_url(f"sqlite:///{target}").database == str(target)


def test_in_memory_sqlite_is_kept():
    assert resolve_database_url("sqlite://").database in (None, "")
    assert resolve_database_url("sqlite:///:memory:").database == ":memory:"
