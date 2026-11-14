"""Regression tests for the batch B review findings."""


def _arjun(api):  # type: ignore[no-untyped-def]
    return api.as_user("arjun.thapa").get("/api/auth/me").json()["id"]


def _evening(api):  # type: ignore[no-untyped-def]
    api.as_user("daniel.mensah").post("/api/runs", json={"kind": "evening"})


def _row(client, name="Arjun Thapa"):  # type: ignore[no-untyped-def]
    return next(r for r in client.get("/api/roster").json()["rows"] if r["worker"] == name)


def test_committed_databases_are_at_migration_head() -> None:
    import sqlite3
    from pathlib import Path

    heads = sorted(p.name.split("_")[0] for p in Path("migrations/versions").glob("0*.py"))
    for name in ("data/datalens.db", "data/scenario.db"):
        con = sqlite3.connect(name)
        assert con.execute("select version_num from alembic_version").fetchone()[0] == heads[-1], (
            name
        )


def test_unshared_not_today_shows_unknown_not_refer(api) -> None:  # type: ignore[no-untyped-def]
    arjun = _arjun(api)
    api.as_user("sara.ibrahim").post(
        f"/api/health/workers/{arjun}/outcome", json={"outcome": "not_today"}
    )
    _evening(api)
    assert _row(api.as_user("daniel.mensah"))["tier"] == "unknown"


def test_audit_never_carries_health_outcomes_or_unwell_names(api) -> None:  # type: ignore[no-untyped-def]
    arjun = _arjun(api)
    api.as_user("sara.ibrahim").post(
        f"/api/health/workers/{arjun}/outcome", json={"outcome": "not_today"}
    )
    _evening(api)
    api.as_user("hessa.almansoori").put("/api/admin/clock", json={"now": "2026-07-29T17:00:00"})
    api.as_user("arjun.thapa").post("/api/phone/unwell", json={})
    trail = api.as_user("layla.haddad").get("/api/audit").json()["entries"]
    blob = str([e for e in trail if e["action"] in ("fitness_outcome", "reported_unwell")])
    assert "not_today" not in blob and "Arjun" not in blob and str(arjun) not in blob


def test_clinician_cannot_run_hse_actions(api) -> None:  # type: ignore[no-untyped-def]
    clinician = api.as_user("sara.ibrahim")
    wid = next(w for w in api.as_user("layla.haddad").get("/api/warnings").json()["open"])["id"]
    assert (
        clinician.post(f"/api/warnings/{wid}/close", json={"outcome": "false_alarm"}).status_code
        == 403
    )
    assert clinician.post("/api/warnings/scan", json={}).status_code == 403
    assert clinician.post(f"/api/warnings/{wid}/inspection", json={}).status_code == 403


def test_planner_cannot_draft_warning_steps_and_closed_records_cannot_be_drafted(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    wid = next(w for w in hse.get("/api/warnings").json()["open"])["id"]
    assert (
        api.as_user("daniel.mensah").post(f"/api/warnings/{wid}/steps/4/draft", json={}).status_code
        == 403
    )
    hse.post(f"/api/warnings/{wid}/close", json={"outcome": "right"})
    assert hse.post(f"/api/warnings/{wid}/steps/4/draft", json={}).status_code == 409


def test_rescore_does_not_duplicate_swaps_and_shows_the_original_activity(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    _evening(api)
    _evening(api)
    swaps = api.as_user("khalid.alnuaimi").get("/api/swaps").json()
    per_worker = [s["worker"] for s in swaps]
    assert len(per_worker) == len(set(per_worker))
    sid = _row(planner)["swap"]["id"]
    planner.post(f"/api/swaps/{sid}/accept", json={})
    api.as_user("khalid.alnuaimi").post(f"/api/swaps/{sid}/approve", json={})
    approved = next(
        s for s in api.as_user("khalid.alnuaimi").get("/api/swaps").json() if s["id"] == sid
    )
    assert approved["from"] == "Lashing at height on deck"


def test_unscored_crew_is_not_green_and_cannot_be_signed(api) -> None:  # type: ignore[no-untyped-def]
    issuer = api.as_user("priya.raman")
    permit = issuer.get("/api/permits").json()["permits"][0]
    assert permit["crew_status"] == "unscored"
    issuer.post(f"/api/permits/{permit['id']}/assess", json={})
    assert issuer.post(f"/api/permits/{permit['id']}/sign", json={}).status_code == 409


def test_planner_can_settle_a_reassignment_without_a_proposal(api) -> None:  # type: ignore[no-untyped-def]
    _evening(api)
    planner = api.as_user("daniel.mensah")
    row = _row(planner)
    response = planner.post(
        f"/api/assignments/{row['assignment_id']}/keep",
        json={"reason": "Only certified lasher left for bay 30; buddy and extra breaks instead."},
    )
    assert response.status_code == 200
    assert _row(planner)["swap"]["status"] == "declined"


def test_scan_does_not_reopen_the_same_district_episode(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    hse.post("/api/warnings/scan", json={})
    assert len(hse.get("/api/warnings").json()["open"]) == 1


def test_action_line_changes_the_back_test(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    low = hse.post("/api/analytics/backtest", json={"action_line": 1.2}).json()
    high = hse.post("/api/analytics/backtest", json={"action_line": 2.0}).json()
    assert (low["ppv"], low["sensitivity"], low["false_alarms"]) != (
        high["ppv"],
        high["sensitivity"],
        high["false_alarms"],
    )
    assert hse.post("/api/analytics/backtest", json={"action_line": 0}).status_code == 422


def test_sensor_accepts_timezone_timestamps(api) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from app.feeds.ingest import gateway_token
    from app.main import app

    body = {
        "sensor_id": "deck",
        "zone_code": "Berth 2",
        "at": "2026-07-29T15:00:00Z",
        "metric": "wbgt",
        "value": 31.0,
    }
    assert (
        TestClient(app)
        .post("/api/ingest/sensor", json=body, headers={"X-Gateway-Token": gateway_token()})
        .status_code
        == 201
    )


def test_admin_clock_converts_offsets(api) -> None:  # type: ignore[no-untyped-def]
    admin = api.as_user("hessa.almansoori")
    admin.put("/api/admin/clock", json={"now": "2026-07-29T19:00:00+04:00"})
    assert admin.get("/api/meta").json()["site_now"].startswith("2026-07-29T15:00")


def test_layer_build_hides_the_behavioural_group(api) -> None:  # type: ignore[no-untyped-def]
    _evening(api)
    planner = api.as_user("daniel.mensah")
    build = planner.get(f"/api/assignments/{_row(planner)['assignment_id']}/build").json()
    names = [d["name"] for layer in build["layers"] for d in layer["drivers"]]
    assert "safety_behaviour" not in names


def test_worker_decides_whether_to_share(api) -> None:  # type: ignore[no-untyped-def]
    arjun = _arjun(api)
    api.as_user("sara.ibrahim").post(
        f"/api/health/workers/{arjun}/outcome", json={"outcome": "fit"}
    )
    planner = api.as_user("daniel.mensah")
    assert (
        next(
            o for o in planner.get("/api/fitness-outcomes").json() if o["worker"] == "Arjun Thapa"
        )["outcome"]
        == "not shared"
    )
    worker = api.as_user("arjun.thapa")
    outcome = worker.get("/api/phone/me").json()["outcome"]
    assert outcome and outcome["shared"] is False
    assert (
        worker.post(
            "/api/phone/consent", json={"outcome_id": outcome["id"], "share": True}
        ).status_code
        == 200
    )
    assert (
        next(
            o for o in planner.get("/api/fitness-outcomes").json() if o["worker"] == "Arjun Thapa"
        )["outcome"]
        == "fit"
    )


def test_contest_once_and_planner_resolves_it(api) -> None:  # type: ignore[no-untyped-def]
    _evening(api)
    worker = api.as_user("arjun.thapa")
    assert worker.post("/api/phone/contest", json={"text": "I slept well."}).status_code == 201
    assert worker.post("/api/phone/contest", json={"text": "Again."}).status_code == 409
    planner = api.as_user("daniel.mensah")
    contest = _row(planner)["contest"]
    assert (
        planner.post(
            f"/api/contests/{contest['id']}/resolve",
            json={"status": "upheld", "note": "Kept on lashing with a buddy."},
        ).status_code
        == 200
    )
    assert _row(planner)["contest"]["status"] == "upheld"


def test_phone_shows_only_approved_swaps(api) -> None:  # type: ignore[no-untyped-def]
    _evening(api)
    assert api.as_user("arjun.thapa").get("/api/phone/me").json()["swap_to"] is None
    planner = api.as_user("daniel.mensah")
    sid = _row(planner)["swap"]["id"]
    planner.post(f"/api/swaps/{sid}/accept", json={})
    api.as_user("khalid.alnuaimi").post(f"/api/swaps/{sid}/approve", json={})
    assert (
        api.as_user("arjun.thapa").get("/api/phone/me").json()["swap_to"]
        == "Ground twist-lock handling"
    )


def test_step_9_confirm_creates_learning_the_hse_head_can_publish(api, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    wid = next(w for w in hse.get("/api/warnings").json()["open"])["id"]
    hse.post(f"/api/warnings/{wid}/steps/1/confirm", json={"content": "Detection confirmed."})
    assert (
        hse.post(
            f"/api/warnings/{wid}/steps/9/confirm",
            json={
                "content": "Card: keep rooms cool before a night shift. Toolbox: check your room's cooling. SWP: night-time cooling check before heat tier 2 days."
            },
        ).status_code
        == 200
    )
    items = [i for i in hse.get("/api/learning").json()["items"] if i["source_id"] == wid]
    assert items and all(i["status"] == "draft" for i in items)
    card = next(i for i in items if i["kind"] == "card")
    assert hse.post(f"/api/learning/{card['id']}/publish", json={}).status_code == 200
    assert any(
        c["id"] == card["id"] for c in api.as_user("arjun.thapa").get("/api/learning/mine").json()
    )


def test_bad_input_is_4xx_not_500(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    assert api.as_user("khalid.alnuaimi").get("/api/swaps?status=bogus").status_code == 422
    admin = api.as_user("hessa.almansoori")
    assert admin.get("/api/admin/people?role=bogus").status_code == 422
    hse = api.as_user("layla.haddad")
    assert hse.get("/api/audit?limit=-5").status_code == 422
    assert (
        hse.post("/api/analytics/impact", json={"lti_per_year": 1e308, "hot_share": 9}).status_code
        == 422
    )
    foreman = api.as_user("joseph.kariuki")
    bad = {
        "text": "Ladder rung loose on bay 3",
        "zone": "Berth 2",
        "photo": "data:image/jpeg;base64,abc",
    }
    assert foreman.post("/api/incidents", json=bad).status_code == 422
    svg = {
        "text": "Ladder rung loose on bay 3",
        "zone": "Berth 2",
        "photo": "data:image/svg+xml;base64,PHN2Zy8+",
    }
    assert foreman.post("/api/incidents", json=svg).status_code == 422
    assert planner.get("/api/roster").status_code == 200
