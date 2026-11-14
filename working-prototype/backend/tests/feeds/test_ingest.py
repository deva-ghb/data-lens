from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import set_site_now
from app.feeds.csv_connect import confirm_mapping, propose_mapping
from app.feeds.ingest import gateway_token, ingest_sensor_reading
from app.main import app
from app.models import Feed, FeedReading, Permit, PermitEvent, Zone
from app.models.permits import PermitStatus


def _live_permit(session: Session) -> Permit:
    berth = session.scalars(select(Zone).where(Zone.name == "Berth 2")).one()
    permit = session.scalars(
        select(Permit).where(Permit.zone_id == berth.id, Permit.number.like("PTW-260729-N-%"))
    ).first()
    assert permit is not None
    permit.status = PermitStatus.LIVE
    session.flush()
    return permit


def test_wbgt_over_32_for_30_min_creates_permit_event_and_foreman_prompt(scenario: Session) -> None:
    permit = _live_permit(scenario)
    start = datetime(2026, 7, 29, 16, 0)
    set_site_now(scenario, start, None)
    for minutes, value in ((0, 32.4), (10, 32.6), (20, 32.9), (30, 33.1)):
        ingest_sensor_reading(
            scenario, "deck-b2-01", "Berth 2", start + timedelta(minutes=minutes), "wbgt", value
        )
    kinds = [
        e.kind
        for e in scenario.scalars(select(PermitEvent).where(PermitEvent.permit_id == permit.id))
    ]
    assert kinds.count("wbgt_limit") == 1
    assert kinds.count("work_rest_change_pending") == 1
    ingest_sensor_reading(
        scenario, "deck-b2-01", "Berth 2", start + timedelta(minutes=40), "wbgt", 33.0
    )
    kinds = [
        e.kind
        for e in scenario.scalars(select(PermitEvent).where(PermitEvent.permit_id == permit.id))
    ]
    assert kinds.count("wbgt_limit") == 1  # not raised again while it is still over


def test_short_spike_does_not_trip_the_limit(scenario: Session) -> None:
    permit = _live_permit(scenario)
    start = datetime(2026, 7, 29, 16, 0)
    for minutes, value in ((0, 31.0), (10, 32.8), (20, 31.5), (30, 32.4)):
        ingest_sensor_reading(
            scenario, "deck-b2-01", "Berth 2", start + timedelta(minutes=minutes), "wbgt", value
        )
    kinds = [
        e.kind
        for e in scenario.scalars(select(PermitEvent).where(PermitEvent.permit_id == permit.id))
    ]
    assert "wbgt_limit" not in kinds


def test_bad_gateway_token_rejected() -> None:
    client = TestClient(app)
    body = {
        "sensor_id": "deck-b2-01",
        "zone_code": "Berth 2",
        "at": "2026-07-29T16:00:00",
        "metric": "wbgt",
        "value": 31.0,
    }
    response = client.post("/api/ingest/sensor", json=body, headers={"X-Gateway-Token": "wrong"})
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_good_gateway_token_passes_the_gate() -> None:
    client = TestClient(app)
    body = {
        "sensor_id": "deck-b2-01",
        "zone_code": "Nowhere",
        "at": "2026-07-29T16:00:00",
        "metric": "wbgt",
        "value": 31.0,
    }
    response = client.post(
        "/api/ingest/sensor", json=body, headers={"X-Gateway-Token": gateway_token()}
    )
    # The token is accepted; this empty test database has no such zone.
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_free_text_columns_never_loaded(scenario: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.ai.decisions import Decisions
    from app.feeds import csv_connect

    def fake_decide(session, subject_kind, subject_id, input_value, questions):  # type: ignore[no-untyped-def]
        answers = {
            "map_date": {"type": "choice", "name": "map_date", "choice": "at"},
            "free_date": {"type": "predicate", "name": "free_date", "probability": 0.0},
            "map_block": {"type": "choice", "name": "map_block", "choice": "zone"},
            "free_block": {"type": "predicate", "name": "free_block", "probability": 0.0},
            "map_count": {"type": "choice", "name": "map_count", "choice": "value"},
            "free_count": {"type": "predicate", "name": "free_count", "probability": 0.02},
            "map_notes": {"type": "choice", "name": "map_notes", "choice": "ignore"},
            "free_notes": {"type": "predicate", "name": "free_notes", "probability": 0.98},
        }
        return Decisions(1, answers)

    monkeypatch.setattr(csv_connect, "decide", fake_decide)
    text = "date,block,count,notes\n2026-07-20,Camp Block A,3,Ahmed said his chest hurt\n2026-07-21,Camp Block B,1,ok\n"
    proposal = propose_mapping(scenario, "Pharmacy sales", text)
    assert proposal.columns["notes"].free_text is True
    feed = confirm_mapping(scenario, proposal, signal_class="clinical", metric="pharmacy_sales")
    rows = scenario.scalars(select(FeedReading).where(FeedReading.feed_id == feed.id)).all()
    assert len(rows) == 2
    assert all("chest" not in (r.metric or "") for r in rows)
    stored = scenario.get_one(Feed, feed.id)
    assert stored.source.value == "uploaded"
