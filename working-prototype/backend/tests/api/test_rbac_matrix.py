"""Every route, called as every role: 403 exactly when the role sheet says no.

The expected table below is written from the role sheet (user-capabliites.txt and design
section 5.2), not read back from the code, so a guard that drifts from the sheet fails here:
- reads follow "Sees": a role reaches a screen only if it sees that data;
- decisions follow "Decides": only the deciding role may take the action.

A route missing from the table fails the test too, so a new route cannot go unchecked.
"""

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select

from app import db
from app.ai.client import set_transport
from app.models import Permit, WarningRecord
from app.models.warnings import WarningStatus
from tests.conftest import ApiClient

W, F, P, SM, PI, H, C, A, AD = (
    "worker",
    "foreman",
    "planner",
    "shift_manager",
    "permit_issuer",
    "hse_head",
    "clinician",
    "authority",
    "admin",
)
ALL = frozenset({W, F, P, SM, PI, H, C, A, AD})

USER = {
    W: "marco.villanueva",
    F: "joseph.kariuki",
    P: "daniel.mensah",
    SM: "khalid.alnuaimi",
    PI: "priya.raman",
    H: "layla.haddad",
    C: "sara.ibrahim",
    A: "ahmed.alshamsi",
    AD: "hessa.almansoori",
}

TIERS = frozenset({P, H})  # sees tiers and work-term reasons for the site
PERMIT_READERS = frozenset({P, SM, PI, H})  # crew status as counts on a permit
REGISTER = frozenset({P, SM, PI, H, C})  # the activity register and groups, no person data

# (method, path template) -> roles that may call it. {warning} and {permit} are filled
# with real records so that checks made inside a handler are reached.
EXPECTED: dict[tuple[str, str], frozenset[str]] = {
    ("GET", "/api/auth/me"): ALL,
    ("GET", "/api/meta"): ALL,
    ("GET", "/api/home"): ALL,
    ("POST", "/api/home/question"): ALL,
    # Planner: tiers, reasons, controls; accepts or declines swaps.
    ("POST", "/api/runs"): TIERS,
    ("GET", "/api/roster"): TIERS,
    ("GET", "/api/assignments/{assignment_id}/build"): TIERS,
    ("GET", "/api/risk-split"): TIERS,
    ("POST", "/api/swaps/{swap_id}/accept"): frozenset({P}),
    ("POST", "/api/swaps/{swap_id}/decline"): frozenset({P}),
    ("POST", "/api/assignments/{assignment_id}/keep"): frozenset({P}),
    ("POST", "/api/contests/{contest_id}/resolve"): frozenset({P}),
    ("GET", "/api/fitness-outcomes"): frozenset({P, H}),
    # Shift manager: sees the planner's proposals and approves a swap.
    ("GET", "/api/swaps"): frozenset({P, SM, H}),
    ("POST", "/api/swaps/{swap_id}/approve"): frozenset({SM}),
    ("POST", "/api/swaps/{swap_id}/reject"): frozenset({SM}),
    # Register and groups carry no person data.
    ("GET", "/api/activities"): REGISTER,
    ("GET", "/api/activities/{activity_id}"): REGISTER,
    ("GET", "/api/groups"): REGISTER,
    # Permit issuer: signs, holds or sends back; edits drafted conditions.
    ("GET", "/api/permits"): PERMIT_READERS,
    ("GET", "/api/permits/{permit}"): PERMIT_READERS,
    ("GET", "/api/permits/{permit}/people-factor.json"): PERMIT_READERS,
    ("POST", "/api/permits/{permit}/conditions"): frozenset({PI}),
    ("PATCH", "/api/permits/{permit}/conditions/{condition_id}"): frozenset({PI}),
    ("POST", "/api/permits/{permit}/{move}"): frozenset({PI}),
    # HSE head: every record; confirms warning sections, creates actions, shares lessons.
    ("GET", "/api/warnings"): frozenset({H}),
    ("POST", "/api/warnings/scan"): frozenset({H}),
    ("GET", "/api/warnings/{warning}"): frozenset({H, PI, F}),
    ("POST", "/api/warnings/{warning}/steps/{n}/draft"): frozenset({H}),
    ("POST", "/api/warnings/{warning}/steps/1/confirm"): frozenset({H}),
    ("POST", "/api/warnings/{warning}/steps/6/confirm"): frozenset({F, H}),
    ("POST", "/api/warnings/{warning}/steps/8/confirm"): frozenset({PI}),
    ("POST", "/api/warnings/{warning}/close"): frozenset({H}),
    ("POST", "/api/warnings/{warning}/inspection"): frozenset({H}),
    ("POST", "/api/incidents"): ALL,
    ("GET", "/api/incidents"): frozenset({H, C}),
    ("GET", "/api/incidents/{kind}/{record_id}"): frozenset({H, C}),
    ("POST", "/api/incidents/{kind}/{record_id}/confirm"): frozenset({H}),
    ("GET", "/api/inspections"): frozenset({F, H, C}),
    ("POST", "/api/inspections/{inspection_id}/checks/{check_id}"): frozenset({F, H}),
    ("GET", "/api/actions"): frozenset({F, P, H, C}),
    ("POST", "/api/actions"): frozenset({H}),
    ("GET", "/api/action-owners"): frozenset({H}),
    ("GET", "/api/learning"): frozenset({F, H, C}),
    ("POST", "/api/learning/{item_id}/publish"): frozenset({H}),
    ("GET", "/api/learning/mine"): ALL,
    ("POST", "/api/learning/{item_id}/read"): ALL,
    ("GET", "/api/analytics/validation"): frozenset({H, C}),
    ("POST", "/api/analytics/backtest"): frozenset({H}),
    ("GET", "/api/analytics/impact"): frozenset({H, C}),
    ("POST", "/api/analytics/impact"): frozenset({H, C}),
    # Clinician: health detail and lab trends; has the final word on health.
    ("GET", "/api/health/screening"): frozenset({C}),
    ("GET", "/api/health/workers/{person_id}"): frozenset({C}),
    ("POST", "/api/health/workers/{person_id}/outcome"): frozenset({C}),
    # Authority: district and employer aggregates and the audit trail.
    ("GET", "/api/district"): frozenset({H, C, A}),
    ("GET", "/api/authority/employers"): frozenset({H, C, A}),
    ("GET", "/api/audit"): frozenset({H, A}),
    ("GET", "/api/governance"): frozenset({H, C, A, AD}),
    ("PUT", "/api/governance/threshold"): frozenset({H, AD}),
    ("PUT", "/api/governance/autonomy"): frozenset({H, AD}),
    ("POST", "/api/governance/weights/{version_id}/approve"): frozenset({H, AD}),
    ("GET", "/api/signals"): frozenset({H, AD}),
    ("POST", "/api/signals/connect"): frozenset({H, AD}),
    ("POST", "/api/signals/connect/{pid}/confirm"): frozenset({H, AD}),
    # Admin: onboards people and runs the site clock.
    ("PUT", "/api/admin/clock"): frozenset({AD}),
    ("GET", "/api/admin/people"): frozenset({AD}),
    ("POST", "/api/admin/people"): frozenset({AD}),
    ("PATCH", "/api/admin/people/{person_id}"): frozenset({AD}),
    # Foreman: actions for the crew; confirms work-rest changes and buddy pairs.
    ("GET", "/api/phone/foreman"): frozenset({F}),
    ("POST", "/api/phone/foreman/confirm/{event_id}"): frozenset({F}),
    # A person's own phone: every signed-in person has one; there is no one else's.
    ("GET", "/api/phone/me"): ALL,
    ("POST", "/api/phone/consent"): ALL,
    ("POST", "/api/phone/checkin"): ALL,
    ("POST", "/api/phone/contest"): ALL,
    ("POST", "/api/phone/unwell"): ALL,
}

# Not role-gated by design: signing in and out, the device feed (its own key), the service
# probe, photos (an unguessable key handed out only with a record the role may see), and an
# action update, which turns on who owns the action rather than on the role.
OUT_OF_SCOPE = {
    ("PATCH", "/api/actions/{action_id}"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/ingest/sensor"),
    ("GET", "/api/health"),
    ("GET", "/api/media/{key}"),
}

# Routes whose template uses a placeholder the sweep fills with a real record.
RENAMED = {
    "/api/permits/{permit_id}": "/api/permits/{permit}",
    "/api/permits/{permit_id}/people-factor.json": "/api/permits/{permit}/people-factor.json",
    "/api/permits/{permit_id}/conditions": "/api/permits/{permit}/conditions",
    "/api/permits/{permit_id}/conditions/{condition_id}": (
        "/api/permits/{permit}/conditions/{condition_id}"
    ),
    "/api/permits/{permit_id}/{move}": "/api/permits/{permit}/{move}",
    "/api/warnings/{warning_id}": "/api/warnings/{warning}",
    "/api/warnings/{warning_id}/steps/{n}/draft": "/api/warnings/{warning}/steps/{n}/draft",
    "/api/warnings/{warning_id}/close": "/api/warnings/{warning}/close",
    "/api/warnings/{warning_id}/inspection": "/api/warnings/{warning}/inspection",
}
STEP_CONFIRM = "/api/warnings/{warning_id}/steps/{n}/confirm"


def _app_routes() -> set[tuple[str, str]]:
    from app.main import app

    def walk(routes: list[Any], prefix: str = "") -> Iterator[tuple[str, APIRoute]]:
        for r in routes:
            if isinstance(r, APIRoute):
                yield prefix, r
            elif hasattr(r, "original_router"):
                ctx = getattr(r, "include_context", None)
                yield from walk(
                    r.original_router.routes, prefix + (getattr(ctx, "prefix", "") or "")
                )
            elif hasattr(r, "routes"):
                yield from walk(r.routes, prefix)

    return {(m, prefix + r.path) for prefix, r in walk(app.routes) for m in r.methods}


def test_every_route_is_in_the_table() -> None:
    covered = {(m, RENAMED.get(p, p)) for m, p in EXPECTED} | OUT_OF_SCOPE
    expected_paths = set()
    for method, path in _app_routes():
        if path == STEP_CONFIRM:
            continue
        expected_paths.add((method, RENAMED.get(path, path)))
    missing = sorted(expected_paths - covered - {(m, p) for m, p in EXPECTED})
    assert missing == [], f"routes with no expected access: {missing}"


@pytest.fixture
def offline_ai() -> Iterator[None]:
    """The copilot answers 'unavailable', so nothing leaves the machine."""
    set_transport(httpx.MockTransport(lambda request: httpx.Response(503)))
    yield
    set_transport(None)


def _fill(template: str) -> str:
    with db.SessionLocal() as s:
        warning = s.scalars(
            select(WarningRecord).where(WarningRecord.status == WarningStatus.OPEN)
        ).first()
        permit = s.scalars(select(Permit).order_by(Permit.id.desc())).first()
    assert warning is not None and permit is not None
    filled = template.replace("{warning}", str(warning.id)).replace("{permit}", str(permit.id))
    filled = filled.replace("{move}", "issue").replace("{kind}", "incident").replace("{n}", "1")
    while "{" in filled:
        start = filled.index("{")
        filled = filled[:start] + "999999" + filled[filled.index("}", start) + 1 :]
    return filled


@pytest.mark.parametrize("role", sorted(ALL))
def test_role_boundaries(role: str, api: ApiClient, offline_ai: None) -> None:
    client = api.as_user(USER[role])
    wrong: list[str] = []
    for (method, template), allowed in sorted(EXPECTED.items()):
        path = _fill(template)
        response = client.request(method, path, json={})
        if role in allowed and response.status_code == 403:
            wrong.append(f"{method} {template}: refused, but the role sheet allows {role}")
        if role not in allowed and response.status_code != 403:
            wrong.append(
                f"{method} {template}: {response.status_code}, but {role} should be refused"
            )
    assert wrong == [], "\n".join(wrong)
