"""Alembic environment.

Target database: `sqlalchemy.url` when set (see app.migrate), otherwise the app engine,
which reads DATABASE_URL.

SQLite foreign keys: the app turns `PRAGMA foreign_keys=ON` for every connection.
Batch migrations on SQLite rebuild a table (create a copy, move rows, drop the old
table, rename). With foreign keys on, dropping the old table can fail or cascade into
child tables. So for SQLite this file switches foreign keys off before the migration
transaction, runs `PRAGMA foreign_key_check` before committing (any orphan row aborts
the migration), and switches foreign keys back on afterwards. The pragma must run
outside a transaction, which is why it is committed on its own first.
"""

from alembic import context
from sqlalchemy import Connection

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app import db

config = context.config
target_metadata = db.Base.metadata


def _engine():
    url = config.get_main_option("sqlalchemy.url")
    return db.make_engine(url) if url else db.engine


def _assert_no_foreign_key_violations(connection: Connection) -> None:
    violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"Migration left rows that break foreign keys: {violations[:10]}")


def run_migrations_offline() -> None:
    context.configure(
        url=_engine().url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = _engine()
    try:
        with engine.connect() as connection:
            is_sqlite = connection.dialect.name == "sqlite"
            if is_sqlite:
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.commit()
            try:
                context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                    render_as_batch=True,
                )
                with context.begin_transaction():
                    context.run_migrations()
                    if is_sqlite:
                        _assert_no_foreign_key_violations(connection)
            finally:
                if is_sqlite:
                    connection.rollback()
                    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                    connection.commit()
    finally:
        if engine is not db.engine:
            engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
