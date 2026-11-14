"""Open an early warning record from a detector signal: the record plus its ten steps."""

from sqlalchemy.orm import Session

from app.audit import audit
from app.detector.detect import ZoneEvaluation, evaluation_time
from app.detector.series import feed_index
from app.models import Person, WarningRecord, WarningStep
from app.models.warnings import WarningStatus, WarningStepStatus

STEP_NAMES = [
    "Detection",
    "Activity and controls",
    "History and patterns",
    "Drivers",
    "Risk assessment",
    "Verify on the ground",
    "Controls",
    "Permits affected",
    "Learning",
    "Close",
]


def evidence(signal: ZoneEvaluation, session: Session) -> dict:
    index = feed_index(session)
    return {
        "day": signal.day.isoformat(),
        "index": signal.index,
        "classes": sorted(signal.classes_agreeing),
        "late_feeds": signal.late_feeds,
        "signals": [
            {
                "feed": c.feed,
                "feed_name": index.feeds[c.feed].name,
                "class": index.feeds[c.feed].signal_class.value,
                "metric": c.metric,
                "zone": index.zone_name[c.zone_id],
                "period_start": c.period_start.isoformat(),
                "period_end": c.period_end.isoformat(),
                "observed": c.observed,
                "expected": c.expected,
                "ratio": c.ratio,
            }
            for c in signal.contributions
        ],
    }


def open_warning(
    session: Session, signal: ZoneEvaluation, actor: Person | None = None
) -> WarningRecord:
    record = WarningRecord(
        opened_at=evaluation_time(signal.day),
        zone_id=signal.zone_id,
        level=signal.level,
        status=WarningStatus.OPEN,
        evidence_json=evidence(signal, session),
    )
    session.add(record)
    session.flush()
    for step in range(1, 11):
        session.add(WarningStep(warning_id=record.id, step=step, status=WarningStepStatus.PENDING))
    session.flush()
    audit(
        session,
        actor,
        "warning_opened",
        "warning",
        str(record.id),
        evidence={"zone_id": signal.zone_id, "level": str(signal.level), "index": signal.index},
    )
    return record
