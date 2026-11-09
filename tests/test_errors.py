from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.deps import current_user
from app.errors import register_error_handlers
from tests.conftest import H, USER_ID


class Body(BaseModel):
    count: int


def make_client() -> TestClient:
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/whoami")
    def whoami(uid: UUID = Depends(current_user)):
        return {"user_id": str(uid)}

    @test_app.post("/echo")
    def echo(body: Body):
        return body

    return TestClient(test_app)


def test_missing_user_id_returns_400():
    resp = make_client().get("/whoami")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "bad_user_id"


def test_malformed_user_id_returns_400():
    resp = make_client().get("/whoami", headers={"X-User-Id": "not-a-uuid"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "bad_user_id"


def test_valid_user_id_passes():
    resp = make_client().get("/whoami", headers=H)
    assert resp.status_code == 200
    assert resp.json() == {"user_id": USER_ID}


def test_validation_error_uses_error_format():
    resp = make_client().post("/echo", json={"count": "many"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"
