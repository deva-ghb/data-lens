from sqlalchemy import text

from app.db import engine, get_session


def test_sqlite_foreign_keys_are_on():
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_get_session_yields_and_closes_a_session():
    generator = get_session()
    session = next(generator)
    assert session.execute(text("SELECT 1")).scalar() == 1
    generator.close()
