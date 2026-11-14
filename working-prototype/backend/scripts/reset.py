"""Restore the scenario: copy backend/data/scenario.db over backend/data/datalens.db.

Usage: uv run python scripts/reset.py   (stop the app first)
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import BACKEND_DIR  # noqa: E402


def reset(scenario: Path, live: Path) -> None:
    for suffix in ("-wal", "-shm"):
        Path(str(live) + suffix).unlink(missing_ok=True)
    shutil.copyfile(scenario, live)


if __name__ == "__main__":
    reset(BACKEND_DIR / "data" / "scenario.db", BACKEND_DIR / "data" / "datalens.db")
    print("Scenario restored: site clock 28 July 2026, 18:00 local.")
