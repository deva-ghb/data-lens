from typing import Any

import pytest

from app.ai.drafts import unavailable_draft
from app.api import warnings as warnings_api
from app.models.ai import AiDraftStatus


@pytest.fixture
def fake_ai(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fake(
        session, kind, subject_kind, subject_id, context, language="en", actor_id=None, fresh=False
    ):  # type: ignore[no-untyped-def]
        seen[kind] = context
        draft = unavailable_draft(kind, subject_kind, subject_id)
        draft.content = f"Draft for {kind}"
        draft.status = AiDraftStatus.DRAFT
        draft.confidence = 0.7
        from datetime import datetime

        draft.created_at = datetime(2026, 7, 28, 14)
        draft.prompt_version = "1"
        draft.model = "fake"
        draft.deployment = "fake"
        session.add(draft)
        session.flush()
        return draft

    monkeypatch.setattr(warnings_api, "get_or_draft", fake)
    return seen


def _camp_c(client):  # type: ignore[no-untyped-def]
    listing = client.get("/api/warnings").json()
    return next(w for w in listing["open"] if w["zone"] == "Camp Block C")


def test_site_view_lists_open_and_closed(api) -> None:  # type: ignore[no-untyped-def]
    listing = api.as_user("layla.haddad").get("/api/warnings").json()
    assert [w["zone"] for w in listing["open"]] == ["Camp Block C"]
    assert {w["outcome"] for w in listing["closed"]} == {"right", "false_alarm"}
    assert any(z["zone"] == "Camp Block C" and z["level"] == "warning" for z in listing["zones"])


def test_record_has_ten_steps_with_named_roles(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    record = hse.get(f"/api/warnings/{_camp_c(hse)['id']}").json()
    assert [s["step"] for s in record["steps"]] == list(range(1, 11))
    assert record["steps"][0]["status"] == "drafted"
    assert "16.1" in record["steps"][0]["draft"]["content"]
    assert record["steps"][7]["confirmer_role"] == "permit_issuer"


def test_steps_confirm_only_by_named_role(api, fake_ai) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    wid = _camp_c(hse)["id"]
    planner = api.as_user("daniel.mensah")
    assert (
        planner.post(f"/api/warnings/{wid}/steps/1/confirm", json={"content": "ok"}).status_code
        == 403
    )
    assert (
        hse.post(f"/api/warnings/{wid}/steps/1/confirm", json={"content": "Confirmed."}).status_code
        == 200
    )
    hse.post(f"/api/warnings/{wid}/steps/8/draft", json={})
    assert (
        hse.post(f"/api/warnings/{wid}/steps/8/confirm", json={"content": "x"}).status_code == 403
    )
    issuer = api.as_user("priya.raman")
    assert (
        issuer.post(
            f"/api/warnings/{wid}/steps/8/confirm", json={"content": "Conditions into permits."}
        ).status_code
        == 200
    )


def test_step_8_writes_draft_conditions_into_affected_permits(api, fake_ai) -> None:  # type: ignore[no-untyped-def]
    api.as_user("daniel.mensah").post("/api/runs", json={"kind": "evening"})
    hse = api.as_user("layla.haddad")
    wid = _camp_c(hse)["id"]
    hse.post(f"/api/warnings/{wid}/steps/8/draft", json={})
    issuer = api.as_user("priya.raman")
    issuer.post(f"/api/warnings/{wid}/steps/8/confirm", json={"content": "ok"})
    board = issuer.get("/api/permits").json()["permits"]
    lash = next(
        p for p in board if p["zone"] == "Berth 2" and p["activity"] == "Lashing at height on deck"
    )
    conditions = issuer.get(f"/api/permits/{lash['id']}").json()["conditions"]
    drafts = [c for c in conditions if c["origin"] == "warning" and c["status"] == "draft"]
    assert any("WBGT" in c["text"] for c in drafts)


def test_step_9_drafts_only_from_confirmed_sections(api, fake_ai) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    wid = _camp_c(hse)["id"]
    hse.post(f"/api/warnings/{wid}/steps/9/draft", json={})
    assert set(fake_ai["warning_step_9"]["confirmed_sections"]) == set()
    hse.post(f"/api/warnings/{wid}/steps/1/confirm", json={"content": "Detection confirmed."})
    hse.post(f"/api/warnings/{wid}/steps/9/draft", json={"refresh": True})
    assert set(fake_ai["warning_step_9"]["confirmed_sections"]) == {"Detection"}


def test_close_requires_outcome(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    wid = _camp_c(hse)["id"]
    assert hse.post(f"/api/warnings/{wid}/close", json={}).status_code == 422
    assert hse.post(f"/api/warnings/{wid}/close", json={"outcome": "right"}).status_code == 200
    assert hse.post(f"/api/warnings/{wid}/close", json={"outcome": "right"}).status_code == 409


def test_district_view_suppresses_small_cells(api) -> None:  # type: ignore[no-untyped-def]
    district = api.as_user("ahmed.alshamsi").get("/api/district").json()
    for row in district["rows"]:
        for cell in row["cells"]:
            assert cell["value"] is None or cell["value"] >= district["threshold"]
    hidden = [c for row in district["rows"] for c in row["cells"] if c["value"] is None]
    assert hidden, "some small cells should be hidden"
    for row in district["rows"]:
        assert row["total"] % 5 == 0


def test_worker_cannot_open_warnings(api) -> None:  # type: ignore[no-untyped-def]
    assert api.as_user("arjun.thapa").get("/api/warnings").status_code == 403
