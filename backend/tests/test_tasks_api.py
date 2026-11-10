from tests.conftest import H
from tests.test_profile_api import NEW_ARRIVAL, post_profile


def patch_step(client, task_id, step_id, done):
    return client.patch(f"/api/tasks/{task_id}/steps/{step_id}", json={"done": done}, headers=H)


def test_task_detail_shape(client):
    post_profile(client, {"has_ssn": False, "has_job_offer": True, "job_type": "CPT"})
    resp = client.get("/api/tasks/ssn", headers=H)
    assert resp.status_code == 200
    body = resp.json()
    assert body["personalized"] is False
    assert [s["id"] for s in body["steps"]] == ["cpt_authorization", "dso_letter", "ssa_visit"]
    assert all(s["sources"][0]["verified_at"] == "2026-11-08" for s in body["steps"])
    assert body["steps"][0]["done"] is False


def test_unknown_task_404(client):
    resp = client.get("/api/tasks/nope", headers=H)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_unknown_step_404(client):
    resp = patch_step(client, "us_phone", "nope", True)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_hidden_step_404(client):
    post_profile(client, {"job_type": "on_campus"})
    resp = patch_step(client, "ssn", "cpt_authorization", True)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_progress_updates(client):
    post_profile(client, NEW_ARRIVAL)
    body = patch_step(client, "us_phone", "choose_plan", True).json()
    assert (body["task_status"], body["progress"]) == ("in_progress", 0.5)
    assert body["step"]["done"] is True
    body = patch_step(client, "us_phone", "activate_sim", True).json()
    assert (body["task_status"], body["progress"]) == ("done", 1.0)
    body = patch_step(client, "us_phone", "activate_sim", False).json()
    assert (body["task_status"], body["progress"]) == ("in_progress", 0.5)


def test_completing_dependency_unblocks(client):
    post_profile(client, NEW_ARRIVAL)
    patch_step(client, "us_phone", "choose_plan", True)
    patch_step(client, "us_phone", "activate_sim", True)
    tasks = {t["id"]: t for t in client.get("/api/checklist", headers=H).json()["tasks"]}
    assert tasks["bank_account"]["blocked_by"] == []


def test_patching_unlisted_task_adds_it(client):
    patch_step(client, "ssn", "dso_letter", True)
    ids = [t["id"] for t in client.get("/api/checklist", headers=H).json()["tasks"]]
    assert "ssn" in ids
