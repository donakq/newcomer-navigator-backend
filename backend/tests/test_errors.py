"""Error format and bearer-token parsing."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.deps import current_session
from app.errors import register_error_handlers


class Body(BaseModel):
    count: int


def make_client() -> TestClient:
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/whoami")
    def whoami(token: str = Depends(current_session)):
        return {"token": token}

    @test_app.post("/echo")
    def echo(body: Body):
        return body

    @test_app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return TestClient(test_app, raise_server_exceptions=False)


def test_missing_token_returns_401():
    resp = make_client().get("/whoami")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


def test_non_bearer_scheme_returns_401():
    resp = make_client().get("/whoami", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401


def test_bearer_token_passes():
    resp = make_client().get("/whoami", headers={"Authorization": "Bearer abc123"})
    assert resp.json() == {"token": "abc123"}


def test_validation_error_uses_error_format():
    resp = make_client().post("/echo", json={"count": "many"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_unhandled_exception_uses_error_format():
    resp = make_client().get("/boom")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "internal_error"
    assert "kaboom" not in resp.text
