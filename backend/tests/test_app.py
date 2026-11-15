"""App-wide behavior: health, error format on unknown routes, documented responses."""

from app.main import app


def test_health_reports_opt_tasks(client):
    data = client.get("/api/health").json()
    assert data["ok"] is True
    assert data["tasks"] == 6  # T01-T06 loaded from catalog/tasks


def test_unknown_route_uses_error_format(client):
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_wrong_method_uses_error_format(client):
    resp = client.delete("/api/schools")
    assert resp.status_code == 405
    assert resp.json()["error"]["code"] == "method_not_allowed"


def test_only_opt_endpoints_exist():
    prefixes = ("/api/health", "/api/auth", "/api/schools", "/api/me", "/api/assistant")
    assert all(path.startswith(prefixes) for path in app.openapi()["paths"])


def test_all_routes_have_response_schemas():
    for path, methods in app.openapi()["paths"].items():
        for method, op in methods.items():
            if "204" in op["responses"]:
                continue  # no body by design (logout, delete account)
            schema = op["responses"]["200"]["content"]["application/json"]["schema"]
            assert schema, f"{method.upper()} {path} has no response schema"
