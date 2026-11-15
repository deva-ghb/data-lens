"""Reset the demo for a recording take.

Usage (from video/): uv run --project ../backend python reset_take.py [--db PATH]

Copies the seeded scenario over the take database, checks the clock reads
28 July 2026, 18:00 site time, and checks the authored texts the take shows
are present (Arjun's reason in English and Nepali, the open Camp Block C record).
Stop the app before running it.
"""

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(BACKEND / "data" / "datalens.db"))
    args = parser.parse_args()
    live = Path(args.db)
    for suffix in ("-wal", "-shm"):
        Path(str(live) + suffix).unlink(missing_ok=True)
    shutil.copyfile(BACKEND / "data" / "scenario.db", live)

    db = sqlite3.connect(live)
    problems = []
    (now,) = db.execute("select now from site_clocks").fetchone() or ("",)
    if not str(now).startswith("2026-07-28 14:00"):
        problems.append(f"site clock is {now}, expected 2026-07-28 14:00 UTC (18:00 site time)")
    langs = {
        row[0]
        for row in db.execute(
            "select language from ai_drafts where kind = 'reason_translation' "
            "and subject_kind = 'assignment-reassign'"
        )
    }
    if not {"en", "ne"} <= langs:
        problems.append(f"Arjun's reason drafts missing: found languages {sorted(langs)}")
    (open_c,) = db.execute(
        "select count(*) from warning_records w join zones z on z.id = w.zone_id "
        "where z.name = 'Camp Block C' and w.status = 'open'"
    ).fetchone()
    if open_c != 1:
        problems.append(f"expected one open Camp Block C record, found {open_c}")
    (runs,) = db.execute("select count(*) from score_runs").fetchone()
    if runs != 0:
        problems.append(f"expected no scoring runs before the take, found {runs}")
    db.close()
    if problems:
        sys.exit("Take not ready:\n- " + "\n- ".join(problems))
    print(f"Take ready: {live} restored, clock 28 Jul 18:00 site time, drafts present.")


if __name__ == "__main__":
    main()
