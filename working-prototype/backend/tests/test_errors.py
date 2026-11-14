from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import ApiError, install_error_handlers
from app.main import app


class LoginBody(BaseModel):
    email: str
    password: str


def make_app() -> FastAPI:
    probe = FastAPI()
    install_error_handlers(probe)

    @probe.post("/login")
    def login(body: LoginBody) -> dict[str, str]:
        return {"email": body.email}

    @probe.get("/items/{item_id}")
    def item(item_id: int) -> dict[str, int]:
        return {"id": item_id}

    @probe.get("/conflict")
    def conflict() -> None:
        raise ApiError(409, "permit_crew_changed", "The crew changed. Please review it again.")

    @probe.get("/plain")
    def plain() -> None:
        raise HTTPException(status_code=403, detail="You cannot see this.")

    @probe.get("/bare")
    def bare() -> None:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Cookie"})

    @probe.get("/boom")
    def boom() -> None:
        raise RuntimeError("internal detail that must not leak")

    return probe


def assert_contract(body: dict) -> None:
    assert set(body) == {"code", "message"}
    assert isinstance(body["code"], str) and body["code"]
    assert isinstance(body["message"], str) and body["message"]


def test_unknown_route_returns_not_found_contract():
    response = TestClient(app).get("/api/does-not-exist")
    assert response.status_code == 404
    assert_contract(response.json())
    assert response.json()["code"] == "not_found"


def test_wrong_method_returns_contract():
    response = TestClient(app).post("/api/health")
    assert response.status_code == 405
    assert_contract(response.json())
    assert response.json()["code"] == "method_not_allowed"


def test_validation_error_returns_invalid_input_with_plain_message():
    response = TestClient(make_app()).post("/login", json={"email": "a@b.c"})
    assert response.status_code == 422
    body = response.json()
    assert_contract(body)
    assert body["code"] == "invalid_input"
    assert "password" in body["message"]
    assert "body" not in body["message"]


def test_malformed_path_value_returns_invalid_input():
    response = TestClient(make_app()).get("/items/abc")
    assert response.status_code == 422
    body = response.json()
    assert_contract(body)
    assert body["code"] == "invalid_input"
    assert "item_id" in body["message"]


def test_api_error_keeps_its_code_and_message():
    response = TestClient(make_app()).get("/conflict")
    assert response.status_code == 409
    assert response.json() == {
        "code": "permit_crew_changed",
        "message": "The crew changed. Please review it again.",
    }


def test_plain_http_exception_maps_status_to_code_and_keeps_message():
    response = TestClient(make_app()).get("/plain")
    assert response.status_code == 403
    assert response.json() == {"code": "forbidden", "message": "You cannot see this."}


def test_http_exception_without_detail_gets_plain_message_and_keeps_headers():
    response = TestClient(make_app()).get("/bare")
    assert response.status_code == 401
    assert_contract(response.json())
    assert response.json()["code"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Cookie"


def test_unexpected_error_returns_contract_without_leaking_detail():
    response = TestClient(make_app(), raise_server_exceptions=False).get("/boom")
    assert response.status_code == 500
    body = response.json()
    assert_contract(body)
    assert body["code"] == "server_error"
    assert "internal detail" not in body["message"]
