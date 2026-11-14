def _roster(client):  # type: ignore[no-untyped-def]
    client.post("/api/runs", json={"kind": "evening"})
    return client.get("/api/roster").json()


def _arjun_row(roster):  # type: ignore[no-untyped-def]
    return next(r for r in roster["rows"] if r["worker"] == "Arjun Thapa")


def test_planner_sees_reason_not_diagnosis(api) -> None:  # type: ignore[no-untyped-def]
    roster = _roster(api.as_user("daniel.mensah"))
    row = _arjun_row(roster)
    assert row["tier"] == "reassign"
    assert row["r"] == 1.94
    assert "Third night in a row" in row["reason"] or "night" in row["reason"].lower()
    blob = str(roster).lower()
    for word in (
        "creatinine",
        "lab result",
        "lab panel",
        "diagnos",
        "nationality",
        "group_code",
        "new_contractor",
        "training path",
    ):
        assert word not in blob
    assert roster["tier_counts"]["reassign"] == 3
    assert roster["budget"]["shown"] == 3


def test_worker_cannot_read_the_roster(api) -> None:  # type: ignore[no-untyped-def]
    assert api.as_user("arjun.thapa").get("/api/roster").status_code == 403


def test_layer_build_matches_the_walkthrough(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    row = _arjun_row(_roster(planner))
    build = planner.get(f"/api/assignments/{row['assignment_id']}/build").json()
    assert [layer["name"] for layer in build["layers"]] == [
        "intrinsic",
        "control",
        "condition",
        "profile",
    ]
    assert build["thresholds"] == [1.3, 1.9]
    assert build["r"] == 1.94


def test_decline_requires_reason(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    swap = _arjun_row(_roster(planner))["swap"]
    response = planner.post(f"/api/swaps/{swap['id']}/decline", json={"reason": " "})
    assert response.status_code == 422


def test_shift_manager_approval_applies_swap_and_audits_with_token(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    row = _arjun_row(_roster(planner))
    swap = row["swap"]
    assert planner.post(f"/api/swaps/{swap['id']}/accept", json={}).status_code == 200
    manager = api.as_user("khalid.alnuaimi")
    pending = manager.get("/api/swaps?status=accepted").json()
    assert any(p["id"] == swap["id"] for p in pending)
    assert manager.post(f"/api/swaps/{swap['id']}/approve", json={}).status_code == 200
    after = _arjun_row(planner.get("/api/roster").json())
    assert after["activity"] == "Ground twist-lock handling"
    audit = api.as_user("ahmed.alshamsi").get("/api/audit?action=swap_approved").json()
    assert audit["entries"] and all("Arjun" not in str(e) for e in audit["entries"])
    assert audit["entries"][0]["subject_ref"].startswith("st-")


def test_decline_after_approval_returns_409(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    swap = _arjun_row(_roster(planner))["swap"]
    planner.post(f"/api/swaps/{swap['id']}/accept", json={})
    api.as_user("khalid.alnuaimi").post(f"/api/swaps/{swap['id']}/approve", json={})
    response = planner.post(f"/api/swaps/{swap['id']}/decline", json={"reason": "Changed my mind"})
    assert response.status_code == 409
    assert response.json()["code"] == "conflict"


def test_planner_cannot_approve_own_swap(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    swap = _arjun_row(_roster(planner))["swap"]
    planner.post(f"/api/swaps/{swap['id']}/accept", json={})
    assert planner.post(f"/api/swaps/{swap['id']}/approve", json={}).status_code == 403


def test_risk_split(api) -> None:  # type: ignore[no-untyped-def]
    planner = api.as_user("daniel.mensah")
    roster = _roster(planner)
    split = planner.get(f"/api/risk-split?shift_id={roster['shift']['id']}").json()
    assert abs(split["conditions_share"] + split["crew_share"] - 1) < 0.01


def test_activities_and_groups(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    activities = hse.get("/api/activities").json()
    lash = next(a for a in activities if a["code"] == "LASH_DECK")
    assert lash["grade"] == 5 and lash["swp_items"] == 14
    detail = hse.get(f"/api/activities/{lash['id']}").json()
    assert detail["uabc_12m"] == {
        "unsafe_act": 11,
        "unsafe_behaviour": 6,
        "unsafe_condition": 7,
        "near_miss": 3,
        "incident": 0,
    }
    assert len(detail["swp"]) == 14
    groups = hse.get("/api/groups").json()
    assert len(groups) == 6
    assert all("members" not in g for g in groups)
    assert next(g for g in groups if g["code"] == "NEW_CONTRACTOR")["multiplier"] == 1.6
