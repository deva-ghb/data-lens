from typing import Any

import pytest

from app.ai.decisions import Decisions
from app.ai.drafts import unavailable_draft
from app.api import incidents as incidents_api
from app.models.ai import AiDraftStatus

PHOTO = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACv/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AN//Z"


@pytest.fixture
def fake_ai(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fake_decide(session, subject_kind, subject_id, input_value, questions):  # type: ignore[no-untyped-def]
        seen["questions"] = [q.name for q in questions]
        seen["input"] = input_value
        answers = {
            "report_type": {
                "type": "choice",
                "name": "report_type",
                "choice": "near_miss",
                "confidence": 0.9,
            },
            "potential_severity": {
                "type": "score",
                "name": "potential_severity",
                "score": 3.2,
                "confidence": 0.6,
            },
            "likelihood": {
                "type": "score",
                "name": "likelihood",
                "score": 2.6,
                "confidence": 0.5,
            },
            "harness_not_clipped": {
                "type": "predicate",
                "name": "harness_not_clipped",
                "probability": 0.81,
            },
            "person_under_load": {
                "type": "predicate",
                "name": "person_under_load",
                "probability": 0.05,
            },
            "missing_ppe": {"type": "predicate", "name": "missing_ppe", "probability": 0.12},
        }
        from datetime import datetime

        from app.models import AiDecision

        row = AiDecision(
            subject_kind=subject_kind,
            subject_id=subject_id,
            model="fake",
            questions_json=[],
            answers_json=list(answers.values()),
            created_at=datetime(2026, 7, 28, 14),
        )
        session.add(row)
        session.flush()
        return Decisions(row.id, answers)

    def fake_draft(
        session, kind, subject_kind, subject_id, context, language="en", actor_id=None, fresh=False
    ):  # type: ignore[no-untyped-def]
        draft = unavailable_draft(kind, subject_kind, subject_id)
        draft.content = "Draft record"
        draft.status = AiDraftStatus.DRAFT
        from datetime import datetime

        draft.created_at = datetime(2026, 7, 28, 14)
        draft.prompt_version = "1"
        draft.model = "fake"
        draft.deployment = "fake"
        session.add(draft)
        session.flush()
        return draft

    monkeypatch.setattr(incidents_api, "decide", fake_decide)
    monkeypatch.setattr(incidents_api, "get_or_draft", fake_draft)
    return seen


def test_report_with_text_and_photo_creates_draft_record(api, fake_ai) -> None:  # type: ignore[no-untyped-def]
    foreman = api.as_user("joseph.kariuki")
    body = {
        "text": "Lasher slipped on the bay 14 ladder, harness caught him.",
        "zone": "Berth 2",
        "activity_code": "LASH_DECK",
        "photo": PHOTO,
    }
    report = foreman.post("/api/incidents", json=body).json()
    assert report["kind"] == "near_miss" and report["status"] == "open"
    assert report["has_photo"] is True
    assert "harness_not_clipped" in fake_ai["questions"]
    detail = (
        api.as_user("layla.haddad").get(f"/api/incidents/{report['kind']}/{report['id']}").json()
    )
    assert detail["record"]["content"] == "Draft record"
    assert detail["photo_checks"]["harness_not_clipped"] == 0.81


def test_risk_matrix_cell_from_likelihood_and_severity_scores(api, fake_ai) -> None:  # type: ignore[no-untyped-def]
    foreman = api.as_user("joseph.kariuki")
    report = foreman.post(
        "/api/incidents", json={"text": "Bar dropped from tier three.", "zone": "Berth 2"}
    ).json()
    detail = (
        api.as_user("layla.haddad").get(f"/api/incidents/{report['kind']}/{report['id']}").json()
    )
    # Scores 3.2 and 2.6 are 0-based indexes: levels 4.2 and 3.6, so cell S4 L4.
    assert detail["risk"] == {"likelihood": 4, "severity": 4, "score": 16}


def test_azure_down_still_saves_report_and_allows_manual_record(api, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(incidents_api, "decide", lambda *a, **k: None)
    monkeypatch.setattr(
        incidents_api,
        "get_or_draft",
        lambda session, kind, subject_kind, subject_id, *a, **k: unavailable_draft(
            kind, subject_kind, subject_id
        ),
    )
    foreman = api.as_user("joseph.kariuki")
    report = foreman.post(
        "/api/incidents", json={"text": "Rung loose on the ladder.", "zone": "Berth 2"}
    ).json()
    assert report["id"]
    hse = api.as_user("layla.haddad")
    detail = hse.get(f"/api/incidents/{report['kind']}/{report['id']}").json()
    assert detail["record"]["status"] == "unavailable"
    confirmed = hse.post(
        f"/api/incidents/{report['kind']}/{report['id']}/confirm",
        json={"content": "Written by hand.", "kind": "hazard"},
    ).json()
    assert confirmed["status"] == "closed"


def test_confirmed_near_miss_counts_toward_control(api, fake_ai) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    lash = next(a for a in hse.get("/api/activities").json() if a["code"] == "LASH_DECK")
    report = (
        api.as_user("joseph.kariuki")
        .post(
            "/api/incidents",
            json={
                "text": "Slipped on the ladder.",
                "zone": "Berth 2",
                "activity_code": "LASH_DECK",
            },
        )
        .json()
    )
    hse.post(
        f"/api/incidents/{report['kind']}/{report['id']}/confirm", json={"content": "Confirmed."}
    )
    after = next(a for a in hse.get("/api/activities").json() if a["code"] == "LASH_DECK")
    assert after["uabc_total_12m"] == lash["uabc_total_12m"] + 1


def test_inspection_result_updates_warning_confidence(api, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        incidents_api,
        "decide",
        lambda *a, **k: Decisions(
            1, {"confirms": {"type": "predicate", "name": "confirms", "probability": 0.92}}
        ),
    )
    hse = api.as_user("layla.haddad")
    wid = next(w for w in hse.get("/api/warnings").json()["open"] if w["zone"] == "Camp Block C")[
        "id"
    ]
    inspection = hse.post(f"/api/warnings/{wid}/inspection", json={}).json()
    assert len(inspection["checks"]) >= 2
    first = inspection["checks"][0]
    result = hse.post(
        f"/api/inspections/{inspection['id']}/checks/{first['id']}",
        json={"result": "confirmed", "note": "11 units still off in rooms C-14 to C-22."},
    ).json()
    assert result["note_confirms"] == 0.92
    record = hse.get(f"/api/warnings/{wid}").json()
    assert record["verification"]["confirmed"] == 1
