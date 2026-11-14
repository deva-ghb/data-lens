from typing import Any

import pytest

from app.ai.drafts import unavailable_draft
from app.api import phone as phone_api
from app.models.ai import AiDraftStatus


def _arjun_id(api):  # type: ignore[no-untyped-def]
    return api.as_user("arjun.thapa").get("/api/auth/me").json()["id"]


def test_only_clinician_reads_lab_trends(api) -> None:  # type: ignore[no-untyped-def]
    arjun = _arjun_id(api)
    assert api.as_user("sara.ibrahim").get(f"/api/health/workers/{arjun}").status_code == 200
    for who in ("daniel.mensah", "layla.haddad", "khalid.alnuaimi"):
        assert api.as_user(who).get(f"/api/health/workers/{arjun}").status_code == 403


def test_outcome_reaches_planner_without_reason(api) -> None:  # type: ignore[no-untyped-def]
    arjun = _arjun_id(api)
    clinician = api.as_user("sara.ibrahim")
    response = clinician.post(
        f"/api/health/workers/{arjun}/outcome",
        json={
            "outcome": "fit_with_restrictions",
            "restriction_text": "No work above the second tier for 7 days",
            "share_with_employer": True,
        },
    )
    assert response.status_code == 201
    outcomes = api.as_user("daniel.mensah").get("/api/fitness-outcomes").json()
    mine = [o for o in outcomes if o["worker"] == "Arjun Thapa"]
    assert mine and mine[0]["outcome"] == "fit_with_restrictions"
    assert "second tier" not in str(outcomes)


def test_not_shared_outcome_shows_as_not_shared_and_engine_treats_unknown(api) -> None:  # type: ignore[no-untyped-def]
    arjun = _arjun_id(api)
    api.as_user("sara.ibrahim").post(
        f"/api/health/workers/{arjun}/outcome",
        json={"outcome": "fit", "share_with_employer": False},
    )
    planner = api.as_user("daniel.mensah")
    assert (
        next(
            o for o in planner.get("/api/fitness-outcomes").json() if o["worker"] == "Arjun Thapa"
        )["outcome"]
        == "not shared"
    )
    planner.post("/api/runs", json={"kind": "evening"})
    row = next(r for r in planner.get("/api/roster").json()["rows"] if r["worker"] == "Arjun Thapa")
    assert row["tier"] == "unknown"


def test_clinician_decision_is_audited(api) -> None:  # type: ignore[no-untyped-def]
    arjun = _arjun_id(api)
    api.as_user("sara.ibrahim").post(
        f"/api/health/workers/{arjun}/outcome", json={"outcome": "fit", "share_with_employer": True}
    )
    entries = api.as_user("layla.haddad").get("/api/audit?action=fitness_outcome").json()["entries"]
    assert entries


@pytest.fixture
def fake_reason(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fake(
        session, kind, subject_kind, subject_id, context, language="en", actor_id=None, fresh=False
    ):  # type: ignore[no-untyped-def]
        from app.ai.drafts import stored_draft

        existing = stored_draft(session, kind, subject_kind, subject_id, language)
        if existing is not None:
            return existing
        seen["language"] = language
        draft = unavailable_draft(kind, subject_kind, subject_id, language)
        draft.content = f"[{language}] reason"
        draft.status = AiDraftStatus.DRAFT
        return draft

    monkeypatch.setattr(phone_api, "get_or_draft", fake)
    return seen


def test_checkin_is_three_taps(api) -> None:  # type: ignore[no-untyped-def]
    worker = api.as_user("arjun.thapa")
    response = worker.post(
        "/api/phone/checkin", json={"sleep_band": "6_to_7", "feeling": "good", "hydration_ok": True}
    )
    assert response.status_code == 201
    assert worker.get("/api/phone/me").json()["checked_in"] is True


def test_worker_sees_reason_in_display_language(api, fake_reason) -> None:  # type: ignore[no-untyped-def]
    api.as_user("daniel.mensah").post("/api/runs", json={"kind": "evening"})
    me = api.as_user("arjun.thapa").get("/api/phone/me").json()
    assert me["tier"] == "reassign"
    assert me["language"] == "ne"
    assert "अर्जुन" in me["reason_local"]  # the seeded Nepali reason
    assert me["reason_en"].startswith("Arjun")
    assert me["swap_to"] is None  # shown to the worker only once the shift manager approves


def test_contest_creates_record_visible_to_planner(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    planner.post("/api/runs", json={"kind": "evening"})
    worker = api.as_user("arjun.thapa")
    assert (
        worker.post(
            "/api/phone/contest", json={"text": "I slept well last night and I know this ladder."}
        ).status_code
        == 201
    )
    row = next(r for r in planner.get("/api/roster").json()["rows"] if r["worker"] == "Arjun Thapa")
    assert row["contest"]["status"] == "open"


def test_unwell_notifies_clinician_and_permit_without_name(api) -> None:  # type: ignore[no-untyped-def]
    api.as_user("daniel.mensah").post("/api/runs", json={"kind": "evening"})
    api.as_user("hessa.almansoori").put("/api/admin/clock", json={"now": "2026-07-29T17:00:00"})
    worker = api.as_user("arjun.thapa")
    assert worker.post("/api/phone/unwell", json={}).status_code == 201
    screening = api.as_user("sara.ibrahim").get("/api/health/screening").json()
    assert any(
        s["worker"] == "Arjun Thapa" and s["why"] == "Reported feeling unwell" for s in screening
    )
    issuer = api.as_user("priya.raman")
    for p in issuer.get("/api/permits").json()["permits"]:
        events = issuer.get(f"/api/permits/{p['id']}").json()["events"]
        for e in events:
            assert "Arjun" not in e["text"] and "Thapa" not in e["text"]
    assert any(
        e["kind"] == "worker_unwell"
        for p in issuer.get("/api/permits").json()["permits"]
        for e in issuer.get(f"/api/permits/{p['id']}").json()["events"]
    )


def test_foreman_sees_actions_not_answers(api) -> None:  # type: ignore[no-untyped-def]
    api.as_user("daniel.mensah").post("/api/runs", json={"kind": "evening"})
    view = api.as_user("joseph.kariuki").get("/api/phone/foreman").json()
    assert view["crew"]
    blob = str(view).lower()
    for word in ("tier", "reassign", "relative risk", "check-in", "sleep", "feeling", "1.94"):
        assert word not in blob
    assert api.as_user("joseph.kariuki").get("/api/roster").status_code == 403


def test_foreman_confirms_work_rest_change(api) -> None:  # type: ignore[no-untyped-def]
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app import db
    from app.feeds.ingest import ingest_sensor_reading
    from app.models import Permit
    from app.models.permits import PermitStatus

    with db.SessionLocal() as session:
        permit = session.scalars(select(Permit).where(Permit.number == "PTW-260729-N-06")).one()
        permit.status = PermitStatus.LIVE
        start = datetime(2026, 7, 29, 15, 0)
        for m, v in ((0, 32.9), (10, 33.0), (20, 32.8), (30, 32.6)):
            ingest_sensor_reading(
                session, "deck", "Berth 2", start + timedelta(minutes=m), "wbgt", v
            )
        session.commit()
    foreman = api.as_user("joseph.kariuki")
    pending = foreman.get("/api/phone/foreman").json()["pending"]
    assert pending
    assert (
        foreman.post(f"/api/phone/foreman/confirm/{pending[0]['id']}", json={}).status_code == 200
    )
    assert foreman.get("/api/phone/foreman").json()["pending"] == []
