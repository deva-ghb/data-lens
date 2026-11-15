from datetime import UTC, date, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.deps import current_user, require_roles
from app.auth.security import hash_password, verify_password
from app.config import settings
from app.errors import install_error_handlers
from app.main import app
from app.models import Employer, EmployerKind, InductionPathway, Person, Role

WELCOME = "welcome@123"


def make_person(session, email="asha.nair@mirsalterminals.com", role=Role.WORKER, **overrides):
    employer = session.query(Employer).first()
    if employer is None:
        employer = Employer(name="Mirsal Terminals", kind=EmployerKind.IN_HOUSE, logo_key="mirsal")
        session.add(employer)
        session.flush()
    values = {
        "employer_id": employer.id,
        "first_name": "Asha",
        "last_name": "Nair",
        "email": email,
        "role": role,
        "job_title": "Operator",
        "hire_date": date(2024, 1, 1),
        "site_arrival_date": date(2024, 1, 15),
        "induction": InductionPathway.SITE,
        "display_language": "ar",
        "password_hash": hash_password(WELCOME),
    }
    values.update(overrides)
    person = Person(**values)
    session.add(person)
    session.commit()
    return person


def login(client, email="asha.nair@mirsalterminals.com", password=WELCOME):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_hash_password_uses_argon2_and_verifies():
    hashed = hash_password(WELCOME)
    assert hashed.startswith("$argon2")
    assert hashed != WELCOME
    assert verify_password(WELCOME, hashed)
    assert not verify_password("welcome@124", hashed)
    assert not verify_password(WELCOME, "not a hash")


def test_login_with_welcome_password_succeeds(session):
    person = make_person(session)
    client = TestClient(app)

    response = login(client)

    assert response.status_code == 200
    assert response.json() == {
        "id": person.id,
        "name": "Asha Nair",
        "role": "worker",
        "employer": "Mirsal Terminals",
        "email": "asha.nair@mirsalterminals.com",
        "display_language": "ar",
    }
    cookie = response.headers["set-cookie"].lower()
    assert "dl_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "secure" not in cookie
    assert f"max-age={12 * 3600}" in cookie

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == response.json()


def test_login_token_is_a_signed_twelve_hour_token(session):
    person = make_person(session)
    client = TestClient(app)
    login(client)
    claims = jwt.decode(client.cookies["dl_session"], settings.jwt_secret, algorithms=["HS256"])
    assert claims["sub"] == str(person.id)
    lifetime = claims["exp"] - datetime.now(UTC).timestamp()
    assert 12 * 3600 - 60 < lifetime <= 12 * 3600


def test_login_with_wrong_password_returns_401_without_revealing_which_field(session):
    make_person(session)
    client = TestClient(app)

    wrong_password = login(client, password="nope")
    unknown_email = login(client, email="nobody@mirsalterminals.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["code"] == "unauthorized"
    assert "set-cookie" not in wrong_password.headers
    assert "password" not in wrong_password.json()["message"].lower()
    assert "email" not in wrong_password.json()["message"].lower()


def test_email_login_is_case_insensitive(session):
    make_person(session)
    client = TestClient(app)
    response = login(client, email="  Asha.NAIR@MirsalTerminals.com ")
    assert response.status_code == 200
    assert response.json()["email"] == "asha.nair@mirsalterminals.com"


def test_inactive_person_cannot_log_in_with_the_same_generic_message(session):
    make_person(session, active=False)
    client = TestClient(app)
    inactive = login(client)
    unknown = login(client, email="nobody@mirsalterminals.com")
    assert inactive.status_code == 401
    assert inactive.json() == unknown.json()


def test_me_without_a_session_returns_401():
    response = TestClient(app).get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_me_rejects_a_forged_or_expired_token(session):
    person = make_person(session)
    now = datetime.now(UTC)
    forged = jwt.encode(
        {"sub": str(person.id), "exp": now + timedelta(hours=1)},
        "a-different-secret-of-at-least-32-bytes",
        "HS256",
    )
    expired = jwt.encode(
        {"sub": str(person.id), "exp": now - timedelta(seconds=1)}, settings.jwt_secret, "HS256"
    )
    for token in (forged, expired, "garbage"):
        client = TestClient(app)
        client.cookies.set("dl_session", token)
        assert client.get("/api/auth/me").status_code == 401


def test_session_stops_working_when_the_person_is_deactivated(session):
    person = make_person(session)
    client = TestClient(app)
    login(client)
    person.active = False
    session.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_the_cookie(session):
    make_person(session)
    client = TestClient(app)
    login(client)

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert "dl_session" not in client.cookies
    assert client.get("/api/auth/me").status_code == 401


def guarded_app() -> FastAPI:
    probe = FastAPI()
    install_error_handlers(probe)
    router = APIRouter()

    @router.get("/who")
    def who(user: Annotated[Person, Depends(current_user)]) -> str:
        return user.email

    @router.get("/planner-only", dependencies=[Depends(require_roles(Role.PLANNER, Role.ADMIN))])
    def planner_only() -> str:
        return "ok"

    probe.include_router(router)
    probe.include_router(app.router)
    return probe


@pytest.mark.parametrize(
    ("role", "status"),
    [
        (Role.WORKER, 403),
        (Role.FOREMAN, 403),
        (Role.PLANNER, 200),
        (Role.ADMIN, 200),
    ],
)
def test_require_roles_blocks_other_roles_with_403(session, role, status):
    make_person(session, role=role)
    client = TestClient(guarded_app())
    login(client)

    response = client.get("/planner-only")

    assert response.status_code == status
    if status == 403:
        assert response.json()["code"] == "forbidden"


def test_require_roles_without_a_session_returns_401():
    assert TestClient(guarded_app()).get("/planner-only").status_code == 401


def test_session_cookie_is_secure_when_hosted_over_https(session, monkeypatch):
    make_person(session)
    session.commit()
    monkeypatch.setattr(settings, "cookie_secure", True)
    response = login(TestClient(app))
    assert response.status_code == 200
    assert "secure" in response.headers["set-cookie"].lower()


def test_session_cookie_is_not_secure_by_default_for_local_http(session):
    make_person(session)
    session.commit()
    response = login(TestClient(app))
    assert "secure" not in response.headers["set-cookie"].lower()
