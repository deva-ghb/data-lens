from typing import Any

import pytest

from app.ai.drafts import unavailable_draft
from app.api import home as home_api


@pytest.fixture
def echo_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(
        session,
        kind,
        subject_kind,
        subject_id,
        context: dict[str, Any],
        language="en",
        actor_id=None,
    ):  # type: ignore[no-untyped-def]
        draft = unavailable_draft(kind, subject_kind, subject_id)
        draft.content = ",".join(sorted(context))
        draft.status = "draft"
        return draft

    monkeypatch.setattr(home_api, "get_or_draft", fake)


def test_home_brief_is_role_specific(api, echo_brief) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah").get("/api/home").json()
    clinician = api.as_user("sara.ibrahim").get("/api/home").json()
    assert "site_tiers" in planner["brief"]["content"]
    assert "health_detail" not in planner["brief"]["content"]
    assert "health_detail" in clinician["brief"]["content"]
    assert planner["role"] == "planner"


def test_home_decisions_point_at_real_work(api, echo_brief) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad").get("/api/home").json()
    titles = " ".join(d["title"] for d in hse["decisions"])
    assert "Camp Block C" in titles
    planner = api.as_user("daniel.mensah")
    planner.post("/api/runs", json={"kind": "evening"})
    decisions = planner.get("/api/home").json()["decisions"]
    assert 1 <= len(decisions) <= 3
    assert any("Marco Villanueva" in d["title"] for d in decisions)


def test_meta_reports_site_clock_and_focus_shift(api) -> None:  # type: ignore[no-untyped-def]
    meta = api.as_user("hessa.almansoori").get("/api/meta").json()
    assert meta["site_now"].startswith("2026-07-28T14:00")
    assert meta["site_now_local"].startswith("2026-07-28T18:00")
    assert meta["next_shift"]["label"]


def test_home_requires_sign_in(api) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/api/home")
    assert response.status_code == 401


def test_issuer_is_sent_to_the_warning_section_only_they_sign(api, echo_brief) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    warning = hse.get("/api/warnings").json()["open"][0]
    for n in (1, 2, 3, 4, 5, 6, 7):
        r = hse.post(
            f"/api/warnings/{warning['id']}/steps/{n}/confirm", json={"content": f"Section {n}."}
        )
        assert r.status_code == 200, r.text
    decisions = api.as_user("priya.raman").get("/api/home").json()["decisions"]
    assert decisions[0]["link"] == f"/warnings/{warning['id']}"
    assert "permits affected" in decisions[0]["title"].lower()


def test_shift_manager_decision_opens_the_swaps_screen(api, echo_brief) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    planner.post("/api/runs", json={"kind": "evening"})
    roster = planner.get("/api/roster").json()
    swap = next(r["swap"] for r in roster["rows"] if r.get("swap"))
    assert planner.post(f"/api/swaps/{swap['id']}/accept", json={}).status_code == 200
    decisions = api.as_user("khalid.alnuaimi").get("/api/home").json()["decisions"]
    assert decisions and all(d["link"] == "/swaps" for d in decisions)
