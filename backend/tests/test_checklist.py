from uuid import UUID

from app.services.store import get_store
from tests.conftest import H, USER_ID
from tests.test_profile_api import NEW_ARRIVAL, post_profile


def checklist_ids(client):
    return [t["id"] for t in client.get("/api/checklist", headers=H).json()["tasks"]]


def test_unmatched_not_started_task_removed(client):
    post_profile(client, NEW_ARRIVAL)
    diff = post_profile(client, {"has_us_phone": True}).json()["checklist_diff"]
    assert "us_phone" in diff["removed"]
    assert "us_phone" not in checklist_ids(client)


def test_started_task_flagged_not_removed(client):
    post_profile(client, NEW_ARRIVAL)
    get_store().set_step(UUID(USER_ID), "us_phone", "choose_plan", True)
    diff = post_profile(client, {"has_us_phone": True}).json()["checklist_diff"]
    assert "us_phone" in diff["flagged"]
    tasks = {t["id"]: t for t in client.get("/api/checklist", headers=H).json()["tasks"]}
    assert tasks["us_phone"]["maybe_not_applicable"] is True


def test_dismissed_task_not_readded(client):
    post_profile(client, NEW_ARRIVAL)
    resp = client.post("/api/checklist/bank_account", json={"action": "dismiss"}, headers=H)
    assert resp.status_code == 200
    diff = post_profile(client, {"school": "UW"}).json()["checklist_diff"]
    assert "bank_account" not in diff["added"]
    assert "bank_account" not in checklist_ids(client)


def test_manual_add(client):
    resp = client.post("/api/checklist/ssn", json={"action": "add"}, headers=H)
    assert resp.status_code == 200
    assert resp.json()["task"]["id"] == "ssn"
    assert "ssn" in checklist_ids(client)


def test_manual_add_unknown_task_404(client):
    resp = client.post("/api/checklist/nope", json={"action": "add"}, headers=H)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_checklist_item_fields(client):
    post_profile(client, NEW_ARRIVAL)
    tasks = {t["id"]: t for t in client.get("/api/checklist", headers=H).json()["tasks"]}
    bank = tasks["bank_account"]
    assert bank["reason"].startswith("You need a US bank account")
    assert bank["blocked_by"] == ["us_phone"]
    assert bank["progress"] == 0.0
    assert bank["status"] == "not_started"
