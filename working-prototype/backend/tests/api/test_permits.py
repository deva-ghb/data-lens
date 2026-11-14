def _night_permits(client):  # type: ignore[no-untyped-def]
    board = client.get("/api/permits").json()
    return [p for p in board["permits"] if p["number"].startswith("PTW-260729-N")]


def _lash_permit(client):  # type: ignore[no-untyped-def]
    return next(
        p
        for p in _night_permits(client)
        if p["activity"] == "Lashing at height on deck" and p["zone"] == "Berth 2"
    )


def _scored(api):  # type: ignore[no-untyped-def]
    api.as_user("daniel.mensah").post("/api/runs", json={"kind": "evening"})


def test_permit_shows_counts_never_names(api) -> None:  # type: ignore[no-untyped-def]
    _scored(api)
    issuer = api.as_user("priya.raman")
    permit = _lash_permit(issuer)
    detail = issuer.get(f"/api/permits/{permit['id']}").json()
    assert detail["people_factor"]["readiness"]["reassign"] >= 1
    assert detail["people_factor"]["crew_status"] == "red"
    assert "arjun" not in str(detail).lower() and "thapa" not in str(detail).lower()


def test_red_crew_blocks_issue_with_409(api) -> None:  # type: ignore[no-untyped-def]
    _scored(api)
    issuer = api.as_user("priya.raman")
    permit = _lash_permit(issuer)
    assert issuer.post(f"/api/permits/{permit['id']}/assess", json={}).status_code == 200
    response = issuer.post(f"/api/permits/{permit['id']}/sign", json={})
    assert response.status_code == 409
    assert "reassign" in response.json()["message"].lower()


def test_sign_after_swaps_settled(api) -> None:  # type: ignore[no-untyped-def]
    _scored(api)
    planner = api.as_user("daniel.mensah")
    manager = api.as_user("khalid.alnuaimi")
    for row in planner.get("/api/roster").json()["rows"]:
        if row["swap"] and row["zone"] == "Berth 2":
            planner.post(f"/api/swaps/{row['swap']['id']}/accept", json={})
            manager.post(f"/api/swaps/{row['swap']['id']}/approve", json={})
    issuer = api.as_user("priya.raman")
    permit = _lash_permit(issuer)
    issuer.post(f"/api/permits/{permit['id']}/assess", json={})
    assert issuer.post(f"/api/permits/{permit['id']}/sign", json={}).status_code == 200
    assert issuer.get(f"/api/permits/{permit['id']}").json()["status"] == "issued"


def test_people_factor_json_matches_contract_keys(api) -> None:  # type: ignore[no-untyped-def]
    _scored(api)
    issuer = api.as_user("priya.raman")
    permit = _lash_permit(issuer)
    record = issuer.get(f"/api/permits/{permit['id']}/people-factor.json").json()
    assert set(record) == {
        "permit",
        "readiness_counts",
        "crew_status",
        "drivers",
        "added_controls",
        "confidence",
        "closing_condition",
        "audit_reference",
    }


def test_conditions_drafted_and_issuer_can_edit(api) -> None:  # type: ignore[no-untyped-def]
    _scored(api)
    issuer = api.as_user("priya.raman")
    permit = _lash_permit(issuer)
    added = issuer.post(
        f"/api/permits/{permit['id']}/conditions",
        json={"text": "Suspend if deck WBGT stays over 32 C for 30 minutes"},
    ).json()
    assert added["status"] == "accepted"
    edited = issuer.patch(
        f"/api/permits/{permit['id']}/conditions/{added['id']}",
        json={"text": "Suspend if deck WBGT stays over 31.5 C for 30 minutes"},
    ).json()
    assert edited["status"] == "edited"


def test_lifecycle_rejects_invalid_moves(api) -> None:  # type: ignore[no-untyped-def]
    _scored(api)
    issuer = api.as_user("priya.raman")
    permit = _lash_permit(issuer)
    assert issuer.post(f"/api/permits/{permit['id']}/close", json={}).status_code == 409
    assert (
        issuer.post(f"/api/permits/{permit['id']}/send-back", json={"reason": "x"}).status_code
        == 409
    )


def test_planner_cannot_sign(api) -> None:  # type: ignore[no-untyped-def]
    _scored(api)
    planner = api.as_user("daniel.mensah")
    permit = _lash_permit(api.as_user("priya.raman"))
    assert planner.post(f"/api/permits/{permit['id']}/sign", json={}).status_code == 403
