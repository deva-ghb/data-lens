"""Run Alembic migrations from code, independent of the current working directory."""

from alembic import command
from alembic.config import Config

from app.db import BACKEND_DIR


def alembic_config(database_url: str | None = None) -> Config:
    """An Alembic config for backend/migrations.

    With `database_url`, migrations run against that database instead of the app's
    configured one (used by tests and scripts that build a database elsewhere).
    """
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    if database_url is not None:
        # ConfigParser treats "%" as interpolation, so escape it.
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_to_head(database_url: str | None = None) -> None:
    command.upgrade(alembic_config(database_url), "head")
