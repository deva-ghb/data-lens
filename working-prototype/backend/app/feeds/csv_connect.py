"""Connect a new feed from a CSV file, with the copilot mapping the columns.

For each column the Decisions API answers two questions in one call: which field of the
feed schema it is (date and time, place, the value, or ignore) and whether it holds free
text. Free-text columns are never loaded, whatever the mapping says: notes typed by
people can carry names and health details. A person reviews the mapping and confirms it;
only then is the feed created and its rows loaded.
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.decisions import Choice, Predicate, decide
from app.audit import audit
from app.models import Feed, FeedReading, Person, Zone
from app.models.feeds import FeedSource, SignalClass

FIELDS = [
    ("at", "The date or date and time of the reading"),
    ("zone", "The place the reading belongs to, such as a camp block or berth"),
    ("value", "The number being counted or measured"),
    ("ignore", "Anything else"),
]
FREE_TEXT_LINE = 0.5
SAMPLE_ROWS = 20


@dataclass
class ColumnMap:
    field: str
    free_text: bool
    confidence: float | None = None


@dataclass
class Proposal:
    name: str
    header: list[str]
    rows: list[dict[str, str]]
    columns: dict[str, ColumnMap] = field(default_factory=dict)
    decision_id: int | None = None
    ai_available: bool = True


def _key(column: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in column.strip().lower())


def propose_mapping(session: Session, name: str, csv_text: str) -> Proposal:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = [{k: v for k, v in r.items() if k is not None} for r in reader]
    header = [h for h in (reader.fieldnames or []) if h]
    if not header:
        raise ValueError("The file has no header row.")
    if len(header) > 200:
        raise ValueError("The file has more than 200 columns.")
    proposal = Proposal(name=name, header=header, rows=rows)
    sample = {col: [r.get(col, "") for r in rows[:SAMPLE_ROWS]] for col in header}
    questions = []
    for col in header:
        questions.append(
            Choice(
                f"map_{_key(col)}",
                f"The column '{col}' has these sample values: {sample[col][:8]}. "
                "Which field is it?",
                FIELDS,
            )
        )
        questions.append(
            Predicate(
                f"free_{_key(col)}",
                f"Is the column '{col}' free text typed by a person "
                "(notes, comments, descriptions)?",
            )
        )
    decision = decide(session, "feed_upload", 0, {"columns": header, "sample": sample}, questions)
    if decision is None:
        proposal.ai_available = False
        for col in header:
            proposal.columns[col] = ColumnMap(field="ignore", free_text=True)
        return proposal
    proposal.decision_id = decision.record_id
    for col in header:
        chosen = decision.choice(f"map_{_key(col)}") or "ignore"
        free = (decision.probability(f"free_{_key(col)}") or 0) >= FREE_TEXT_LINE
        proposal.columns[col] = ColumnMap(
            field="ignore" if free else chosen,
            free_text=free,
            confidence=decision.confidence(f"map_{_key(col)}"),
        )
    return proposal


def _parse_time(text: str) -> datetime | None:
    text = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def confirm_mapping(
    session: Session,
    proposal: Proposal,
    signal_class: str,
    metric: str,
    actor: Person | None = None,
) -> Feed:
    by_field = {m.field: col for col, m in proposal.columns.items() if not m.free_text}
    if "at" not in by_field or "value" not in by_field:
        raise ValueError("A feed needs a date column and a value column.")
    base = "UPLOAD_" + _key(proposal.name).upper()[:30]
    code, n = base, 2
    while session.scalar(select(Feed.id).where(Feed.code == code)) is not None:
        code, n = f"{base[:36]}_{n}", n + 1
    feed = Feed(
        code=code,
        name=proposal.name,
        signal_class=SignalClass(signal_class),
        cadence_minutes=1440,
        allowed_delay_minutes=1440,
        location_level="camp block" if "zone" in by_field else "site",
        enabled=True,
        source=FeedSource.UPLOADED,
    )
    session.add(feed)
    session.flush()
    zones = {z.name.lower(): z.id for z in session.scalars(select(Zone))}
    loaded = skipped = 0
    for row in proposal.rows:
        at = _parse_time(row.get(by_field["at"], ""))
        try:
            value = float(row.get(by_field["value"], ""))
        except ValueError:
            value = None
        if at is None or value is None:
            skipped += 1
            continue
        zone_id = (
            zones.get(row.get(by_field.get("zone", ""), "").strip().lower())
            if "zone" in by_field
            else None
        )
        session.add(
            FeedReading(
                feed_id=feed.id,
                zone_id=zone_id,
                at=at,
                metric=metric,
                value=value,
                source=FeedSource.UPLOADED,
            )
        )
        loaded += 1
    session.flush()
    audit(
        session,
        actor,
        "feed_connected",
        "feed",
        str(feed.id),
        evidence={
            "rows_loaded": loaded,
            "rows_skipped": skipped,
            "excluded_free_text": [c for c, m in proposal.columns.items() if m.free_text],
        },
    )
    return feed
