"""Build a fresh scenario database file: migrate, generate, commit."""

from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.db import make_engine
from app.migrate import upgrade_to_head
from seed.generate import generate
from seed.history_ai import write_history
from seed.scenario import SEED


def build_database(path: Path) -> None:
    if path.exists():
        path.unlink()
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    engine = make_engine(url)
    try:
        with Session(engine) as session:
            generate(session, np.random.default_rng(SEED))
            session.commit()
            write_history(session)
            session.commit()
    finally:
        engine.dispose()
