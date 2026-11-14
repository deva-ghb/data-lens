def test_impact_defaults_give_1_6_lti_and_31_workdays(api) -> None:  # type: ignore[no-untyped-def]
    impact = api.as_user("layla.haddad").get("/api/analytics/impact").json()
    assert abs(impact["lti_avoided"] - 1.6) <= 0.1
    assert abs(impact["workdays_avoided"] - 31) <= 1
    custom = (
        api.as_user("layla.haddad")
        .post("/api/analytics/impact", json={**impact["inputs"], "acted_on": 1.0})
        .json()
    )
    assert custom["lti_avoided"] > impact["lti_avoided"]


def test_validation_and_feed_switch_off(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    full = hse.post("/api/analytics/backtest", json={"action_line": 1.5, "feeds_off": []}).json()
    assert full["sensitivity"] == [4, 4]
    degraded = hse.post(
        "/api/analytics/backtest", json={"action_line": 1.5, "feeds_off": ["CLINIC_VISITS"]}
    ).json()
    assert degraded["sensitivity"][0] < 4


def test_threshold_change_is_audited_and_applies_everywhere(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    before = api.as_user("ahmed.alshamsi").get("/api/district").json()
    assert hse.put("/api/governance/threshold", json={"value": 20}).status_code == 200
    after = api.as_user("ahmed.alshamsi").get("/api/district").json()
    assert after["threshold"] == 20
    hidden_before = sum(1 for r in before["rows"] for c in r["cells"] if c["value"] is None)
    hidden_after = sum(1 for r in after["rows"] for c in r["cells"] if c["value"] is None)
    assert hidden_after >= hidden_before
    assert hse.get("/api/audit?action=threshold_changed").json()["entries"]


def test_autonomy_setting_per_action(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    gov = hse.get("/api/governance").json()
    locked = {a["action"] for a in gov["autonomy"] if a["locked"]}
    assert {"reassign_worker", "sign_permit", "health_restriction"} <= locked
    assert (
        hse.put(
            "/api/governance/autonomy", json={"action": "sign_permit", "mode": "do_and_tell"}
        ).status_code
        == 409
    )
    assert (
        hse.put(
            "/api/governance/autonomy", json={"action": "raise_warning", "mode": "do_and_tell"}
        ).status_code
        == 200
    )


def test_authority_sees_redacted_trail_and_counts_of_10_or_more(api) -> None:  # type: ignore[no-untyped-def]
    authority = api.as_user("ahmed.alshamsi")
    trail = authority.get("/api/audit").json()
    assert trail["redacted"] is True
    assert all(e["actor"] is None and e["evidence"] is None for e in trail["entries"])
    employers = authority.get("/api/authority/employers").json()
    for row in employers["rows"]:
        for cell in row["cells"]:
            assert cell["value"] is None or cell["value"] >= employers["threshold"]
    assert authority.get("/api/roster").status_code == 403


def test_no_export_endpoint_for_tiers(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    for path in ("/api/roster.csv", "/api/roster/export", "/api/tiers/export"):
        assert planner.get(path).status_code == 404


def test_signals_list_feeds_with_freshness(api) -> None:  # type: ignore[no-untyped-def]
    signals = api.as_user("layla.haddad").get("/api/signals").json()
    codes = {f["code"] for f in signals["feeds"]}
    assert {"CLINIC_VISITS", "WEATHER", "CAMP_TICKETS", "CHECKINS"} <= codes
    weather = next(f for f in signals["feeds"] if f["code"] == "WEATHER")
    assert weather["signal_class"] == "environmental" and weather["late"] is False


def test_onboarded_person_can_log_in_with_welcome_password(api) -> None:  # type: ignore[no-untyped-def]
    admin = api.as_user("hessa.almansoori")
    created = admin.post(
        "/api/admin/people",
        json={
            "first_name": "Rania",
            "last_name": "Saleh",
            "role": "planner",
            "employer": "Mirsal Terminals",
            "job_title": "Night planner",
        },
    ).json()
    assert created["email"] == "rania.saleh@mirsalterminals.com"
    assert api.as_user("rania.saleh").get("/api/auth/me").json()["role"] == "planner"


def test_only_admin_moves_clock(api) -> None:  # type: ignore[no-untyped-def]
    assert (
        api.as_user("layla.haddad")
        .put("/api/admin/clock", json={"now": "2026-07-29T10:00:00"})
        .status_code
        == 403
    )
    assert (
        api.as_user("hessa.almansoori")
        .put("/api/admin/clock", json={"now": "2026-07-29T10:00:00"})
        .status_code
        == 200
    )


def test_reset_restores_scenario(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import shutil
    import sqlite3

    from scripts.reset import reset

    scenario = tmp_path / "scenario.db"
    live = tmp_path / "datalens.db"
    shutil.copyfile("data/scenario.db", scenario)
    shutil.copyfile("data/scenario.db", live)
    con = sqlite3.connect(live)
    con.execute("update site_clocks set now='2026-08-01 00:00:00'")
    con.commit()
    con.close()
    reset(scenario, live)
    con = sqlite3.connect(live)
    assert con.execute("select now from site_clocks").fetchone()[0].startswith("2026-07-28 14:00")
