"""Rebuild the scenario database.

Usage: uv run python scripts/seed.py --fresh
Writes backend/data/datalens.db from scratch, deterministically.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import BACKEND_DIR  # noqa: E402
from seed.build import build_database  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh", action="store_true", help="delete and rebuild the database")
    parser.add_argument("--out", default=str(BACKEND_DIR / "data" / "datalens.db"))
    args = parser.parse_args()
    if not args.fresh:
        parser.error("pass --fresh to rebuild the database from scratch")
    build_database(Path(args.out))
    print(f"built {args.out}")


if __name__ == "__main__":
    main()
