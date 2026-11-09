from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import register_error_handlers
from app.main import app
from app.services.rules import evaluate
from app.services.store import get_store
from tests.conftest import H, USER_ID
from tests.test_profile_api import NEW_ARRIVAL, post_profile


# Important 1: catalog validated at startup, visible in health
def test_health_reports_catalog(client):
    assert client.get("/api/health").json()["tasks"] == 3


# Important 2: every error uses the error format
def test_unknown_route_uses_error_format(client):
    resp = client.get("/api/nope", headers=H)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_wrong_method_uses_error_format(client):
    resp = client.delete("/api/profile", headers=H)
    assert resp.status_code == 405
    assert resp.json()["error"]["code"] == "method_not_allowed"


def test_unhandled_exception_uses_error_format():
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    resp = TestClient(test_app, raise_server_exceptions=False).get("/boom")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "internal_error"
    assert "kaboom" not in resp.text


# Important 3: a flagged dependency does not block
def test_flagged_dependency_does_not_block(client):
    post_profile(client, NEW_ARRIVAL)
    get_store().set_step(UUID(USER_ID), "us_phone", "choose_plan", True)
    post_profile(client, {"has_us_phone": True})
    tasks = {t["id"]: t for t in client.get("/api/checklist", headers=H).json()["tasks"]}
    assert tasks["us_phone"]["maybe_not_applicable"] is True
    assert tasks["bank_account"]["blocked_by"] == []


# Important 4: every route documents its response shape
def test_all_routes_have_response_schemas():
    spec = app.openapi()
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            schema = op["responses"]["200"]["content"]["application/json"]["schema"]
            assert schema, f"{method.upper()} {path} has no response schema"


# Important 5: `not` does not turn an unanswered question into a match
def test_not_of_unknown_is_false():
    assert evaluate({"not": {"field": "has_ssn", "eq": True}}, {}) is False


def test_not_of_known_still_negates():
    assert evaluate({"not": {"field": "has_ssn", "eq": True}}, {"has_ssn": False}) is True


def test_any_with_one_true_and_one_unknown_is_true():
    cond = {"any": [{"field": "in_us", "eq": True}, {"field": "has_ssn", "eq": False}]}
    assert evaluate(cond, {"in_us": True}) is True
