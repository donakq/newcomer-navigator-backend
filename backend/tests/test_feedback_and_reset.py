"""Assistant feedback (thumbs up / down) and starting over with the old plan kept in history."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.store.sql import Base, SqlStore


def test_thumbs_up_is_saved(client, auth, store):
    body = {"conversation_id": "conv-1", "rating": "UP", "intent": "NEXT_STEP", "scope": "IN",
            "current_page": "checklist"}
    res = client.post("/api/assistant/feedback", json=body, headers=auth)
    assert res.status_code == 201
    assert res.json()["id"]


def test_thumbs_down_with_reasons_and_comment(client, auth):
    body = {"rating": "DOWN", "reasons": ["WRONG_INFO", "UNCLEAR"], "comment": "The deadline looks off."}
    assert client.post("/api/assistant/feedback", json=body, headers=auth).status_code == 201


@pytest.mark.parametrize("body", [
    {"rating": "MEH"},
    {"rating": "DOWN", "reasons": ["NOT_A_REASON"]},
    {"rating": "DOWN", "comment": "x" * 501},
])
def test_bad_feedback_rejected(client, auth, body):
    res = client.post("/api/assistant/feedback", json=body, headers=auth)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


def test_feedback_needs_login(client):
    assert client.post("/api/assistant/feedback", json={"rating": "UP"}).status_code == 401


def test_reset_moves_plan_to_history_and_back_to_onboarding(client, auth):
    before = client.get("/api/me/profile", headers=auth).json()["profile"]
    client.patch("/api/me/tasks/T01", json={"status": "COMPLETED"}, headers=auth)

    assert client.post("/api/me/reset", headers=auth).status_code == 204

    res = client.get("/api/me/profile", headers=auth)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "onboarding_required"

    entries = client.get("/api/me/history", headers=auth).json()["entries"]
    assert len(entries) == 1
    assert entries[0]["profile"]["program_end_date"] == before["program_end_date"]
    assert entries[0]["task_statuses"]["T01"] == "COMPLETED"
    assert entries[0]["archived_at"]


def test_onboarding_after_reset_starts_clean(client, auth):
    client.patch("/api/me/tasks/T01", json={"status": "COMPLETED"}, headers=auth)
    client.post("/api/me/reset", headers=auth)
    body = {"school_id": "uw", "program_end_date": "2027-12-15", "degree_level": "MASTER"}
    assert client.put("/api/me/onboarding", json=body, headers=auth).status_code == 200
    plan = client.get("/api/me/opt-plan", headers=auth).json()
    assert all(t["status"] != "COMPLETED" for t in plan["tasks"])


def test_history_newest_first(client, auth):
    client.post("/api/me/reset", headers=auth)
    body = {"school_id": "uw", "program_end_date": "2027-12-15", "degree_level": "MASTER"}
    client.put("/api/me/onboarding", json=body, headers=auth)
    client.post("/api/me/reset", headers=auth)
    entries = client.get("/api/me/history", headers=auth).json()["entries"]
    assert [e["profile"]["program_end_date"] for e in entries] == ["2027-12-15", "2027-06-11"]


def test_reset_before_onboarding_adds_no_history(client):
    token = client.post("/api/auth/email/verify",
                        json={"email": "new@uw.edu", "code": "000000", "tos_accepted": True}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/me/reset", headers=headers).status_code == 204
    assert client.get("/api/me/history", headers=headers).json()["entries"] == []


def test_delete_account_removes_history_and_feedback(client, auth, store):
    if not isinstance(store, SqlStore):
        pytest.skip("checks database tables")
    client.post("/api/assistant/feedback", json={"rating": "UP"}, headers=auth)
    client.post("/api/me/reset", headers=auth)
    assert client.delete("/api/me", headers=auth).status_code == 204
    with Session(store.engine) as db:
        for table in Base.metadata.sorted_tables:
            assert db.scalar(select(func.count()).select_from(table)) == 0, table.name


def _onboard(client, auth, p="2027-12-15"):
    body = {"school_id": "uw", "program_end_date": p, "degree_level": "MASTER"}
    assert client.put("/api/me/onboarding", json=body, headers=auth).status_code == 200


def test_restore_brings_back_old_plan_and_keeps_current_one(client, auth):
    client.patch("/api/me/tasks/T01", json={"status": "COMPLETED"}, headers=auth)
    client.post("/api/me/reset", headers=auth)
    _onboard(client, auth)
    old = client.get("/api/me/history", headers=auth).json()["entries"][0]

    res = client.post(f"/api/me/history/{old['id']}/restore", headers=auth)
    assert res.status_code == 200
    assert res.json()["profile"]["program_end_date"] == "2027-06-11"

    plan = client.get("/api/me/opt-plan", headers=auth).json()
    assert next(t for t in plan["tasks"] if t["id"] == "T01")["status"] == "COMPLETED"
    # The plan that was current is now in history; the restored one left it.
    entries = client.get("/api/me/history", headers=auth).json()["entries"]
    assert [e["profile"]["program_end_date"] for e in entries] == ["2027-12-15"]


def test_restore_while_not_onboarded_adds_nothing_to_history(client, auth):
    client.post("/api/me/reset", headers=auth)
    entry_id = client.get("/api/me/history", headers=auth).json()["entries"][0]["id"]
    assert client.post(f"/api/me/history/{entry_id}/restore", headers=auth).status_code == 200
    assert client.get("/api/me/history", headers=auth).json()["entries"] == []
    assert client.get("/api/me/profile", headers=auth).status_code == 200


def test_restore_unknown_entry_is_404(client, auth):
    res = client.post("/api/me/history/nope/restore", headers=auth)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_cannot_restore_another_users_plan(client, auth):
    client.post("/api/me/reset", headers=auth)
    entry_id = client.get("/api/me/history", headers=auth).json()["entries"][0]["id"]
    other = client.post("/api/auth/email/verify",
                        json={"email": "other@uw.edu", "code": "000000", "tos_accepted": True}).json()["token"]
    res = client.post(f"/api/me/history/{entry_id}/restore", headers={"Authorization": f"Bearer {other}"})
    assert res.status_code == 404
