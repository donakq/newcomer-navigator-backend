from tests.conftest import H

NEW_ARRIVAL = {"in_us": True, "has_us_phone": False, "has_bank_account": False}


def post_profile(client, answers):
    return client.post("/api/profile", json={"answers": answers}, headers=H)


def test_profile_merge_not_overwrite(client):
    post_profile(client, {"in_us": True})
    post_profile(client, {"has_ssn": False})
    profile = client.get("/api/profile", headers=H).json()["profile"]
    assert profile["in_us"] is True
    assert profile["has_ssn"] is False


def test_unknown_profile_field_422(client):
    resp = post_profile(client, {"ssn_number": "123"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_bad_profile_value_422(client):
    resp = post_profile(client, {"job_type": "astronaut"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_profile_post_returns_diff(client):
    resp = post_profile(client, NEW_ARRIVAL)
    assert resp.status_code == 200
    assert resp.json()["checklist_diff"]["added"] == ["bank_account", "us_phone"]


def test_profile_requires_user_id(client):
    assert client.get("/api/profile").status_code == 400
