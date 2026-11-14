"""Run the back-test sweep on a database and print the six measures.

Usage: uv run python scripts/backtest.py [--db PATH] [--save]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from app.backtest.harness import choose_action_line, sweep  # noqa: E402
from app.db import BACKEND_DIR, make_engine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(BACKEND_DIR / "data" / "datalens.db"))
    parser.add_argument("--save", action="store_true", help="keep the result in the database")
    args = parser.parse_args()
    engine = make_engine(f"sqlite:///{args.db}")
    with Session(engine) as session:
        results = sweep(session)
        chosen = choose_action_line(results)
        for r in results:
            mark = "  <- chosen" if r.action_line == chosen else ""
            leads = ", ".join(f"{k}: {v}" for k, v in r.lead_time_hours.items())
            print(
                f"line {r.action_line:.1f}: found {r.sensitivity[0]}/{r.sensitivity[1]}, "
                f"PPV {r.ppv:.2f}, false alarms/30d {r.false_alarms_per_30d}, "
                f"budget breaches {r.budget_breaches}{mark}\n    lead hours: {leads}"
            )
        if args.save:
            session.commit()
    engine.dispose()


if __name__ == "__main__":
    main()
