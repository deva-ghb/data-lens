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
    assert any("Arjun Thapa" in d["title"] for d in decisions)


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
