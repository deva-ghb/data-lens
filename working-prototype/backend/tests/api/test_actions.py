def _warning_id(client):  # type: ignore[no-untyped-def]
    return next(
        w for w in client.get("/api/warnings").json()["open"] if w["zone"] == "Camp Block C"
    )["id"]


def _owner_id(client):  # type: ignore[no-untyped-def]
    return client.get("/api/auth/me").json()["id"]


def test_action_requires_owner_due_date_and_effectiveness_check(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    wid = _warning_id(hse)
    missing = hse.post(
        "/api/actions",
        json={
            "source_kind": "warning",
            "source_id": wid,
            "title": "Fix cooling",
            "control_level": "engineer",
        },
    )
    assert missing.status_code == 422
    ok = hse.post(
        "/api/actions",
        json={
            "source_kind": "warning",
            "source_id": wid,
            "title": "Repair the 11 cooling units in Camp Block C",
            "control_level": "engineer",
            "owner_id": _owner_id(hse),
            "due_on": "2026-07-29",
            "effectiveness_check_on": "2026-08-02",
        },
    )
    assert ok.status_code == 201


def test_actions_sorted_by_hierarchy_of_controls(api) -> None:  # type: ignore[no-untyped-def]
    actions = api.as_user("layla.haddad").get("/api/actions").json()
    order = ["eliminate", "substitute", "engineer", "administrative", "ppe"]
    levels = [order.index(a["control_level"]) for a in actions]
    assert levels == sorted(levels)
    assert all(a["owner"] for a in actions)


def test_effectiveness_check_closes_linked_warning_on_site_clock(api) -> None:  # type: ignore[no-untyped-def]
    hse = api.as_user("layla.haddad")
    wid = _warning_id(hse)
    action = hse.post(
        "/api/actions",
        json={
            "source_kind": "warning",
            "source_id": wid,
            "title": "Repair the cooling units",
            "control_level": "engineer",
            "owner_id": _owner_id(hse),
            "due_on": "2026-07-29",
            "effectiveness_check_on": "2026-08-02",
        },
    ).json()
    hse.patch(f"/api/actions/{action['id']}", json={"status": "done"})
    early = hse.patch(f"/api/actions/{action['id']}", json={"effective": True})
    assert early.status_code == 409
    api.as_user("hessa.almansoori").put("/api/admin/clock", json={"now": "2026-08-02T08:00:00"})
    assert hse.patch(f"/api/actions/{action['id']}", json={"effective": True}).status_code == 200
    record = hse.get(f"/api/warnings/{wid}").json()
    assert record["status"] == "closed" and record["outcome"] == "right"


def test_read_counts_by_crew_suppressed_below_threshold(api) -> None:  # type: ignore[no-untyped-def]
    learning = api.as_user("layla.haddad").get("/api/learning").json()
    assert learning["items"]
    for item in learning["items"]:
        for cell in item["reads_by_crew"]:
            assert cell["reads"] is None or cell["reads"] >= learning["threshold"]


def test_worker_reads_a_card(api) -> None:  # type: ignore[no-untyped-def]
    worker = api.as_user("arjun.thapa")
    cards = worker.get("/api/learning/mine").json()
    assert cards
    assert worker.post(f"/api/learning/{cards[0]['id']}/read", json={}).status_code == 200
