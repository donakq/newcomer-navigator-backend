"""API contract for OPT MVP v1 (PRD v1.3 section 8.3), served from mock data."""

from datetime import date

from app.opt.timeline import TimelineInput, compute_timeline
from app.mock.opt_demo import demo_params, demo_profile

AUTH = {"Authorization": "Bearer mock-token"}


# --- Auth ---


def test_email_start(client):
    resp = client.post("/api/auth/email/start", json={"email": "student@uw.edu"})
    assert resp.status_code == 200
    assert resp.json()["resend_after_seconds"] == 60


def test_email_start_rejects_bad_email(client):
    resp = client.post("/api/auth/email/start", json={"email": "not-an-email"})
    assert resp.status_code == 422


def test_verify_wrong_code(client):
    body = {"email": "student@uw.edu", "code": "123456", "tos_accepted": True}
    resp = client.post("/api/auth/email/verify", json=body)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_code"


def test_verify_mock_code_returns_token(client):
    body = {"email": "student@uw.edu", "code": "000000", "tos_accepted": True, "timezone": "America/Los_Angeles"}
    data = client.post("/api/auth/email/verify", json=body).json()
    assert data["token"]
    assert data["is_new_user"] in (True, False)


def test_verify_requires_tos(client):
    body = {"email": "student@uw.edu", "code": "000000", "tos_accepted": False}
    assert client.post("/api/auth/email/verify", json=body).status_code == 422


def test_me_requires_login(client):
    resp = client.get("/api/me/profile")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


def test_logout(client):
    assert client.post("/api/auth/logout", headers=AUTH).status_code == 204


# --- Schools ---


def test_school_search_finds_uw(client):
    schools = client.get("/api/schools", params={"q": "washington"}).json()["schools"]
    assert schools[0]["id"] == "uw"
    assert schools[0]["support_status"] == "SUPPORTED"


def test_school_office(client):
    office = client.get("/api/schools/uw/office").json()
    assert office["office_display_name"] == "UW ISS"
    assert office["preferred_channel"] in ("EMAIL", "FORM", "PORTAL")


def test_unknown_school_office_404(client):
    assert client.get("/api/schools/nope/office").status_code == 404


# --- Onboarding and Home ---


def test_onboarding(client):
    body = {"school_id": "uw", "program_end_date": "2027-06-11", "degree_level": "MASTER"}
    profile = client.put("/api/me/onboarding", json=body, headers=AUTH).json()["profile"]
    assert profile["program_end_date"] == "2027-06-11"


def test_onboarding_unsupported_school_409(client):
    body = {"school_id": "other", "program_end_date": "2027-06-11", "degree_level": "MASTER"}
    resp = client.put("/api/me/onboarding", json=body, headers=AUTH)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "unsupported_school"


def test_onboarding_requires_program_end_date(client):
    body = {"school_id": "uw", "degree_level": "MASTER"}
    assert client.put("/api/me/onboarding", json=body, headers=AUTH).status_code == 422


def test_get_profile(client):
    data = client.get("/api/me/profile", headers=AUTH).json()["profile"]
    assert data["school"]["id"] == "uw"
    assert data["stage"] == "PLANNING"
    assert data["offer"]["has_offer"] is True


def test_patch_profile_returns_plan_version(client):
    resp = client.patch("/api/me/profile", json={"program_end_date": "2027-06-20"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["plan_version"] >= 1


def test_delete_account(client):
    assert client.delete("/api/me", headers=AUTH).status_code == 204


# --- Checklist, Select OPT, Status, Offer ---


def test_checklist_modules(client):
    data = client.get("/api/me/checklist", headers=AUTH).json()
    statuses = {m["id"]: m["status"] for m in data["modules"]}
    assert statuses["work_authorization"] == "OPEN"
    assert set(statuses.values()) == {"OPEN", "COMING_SOON"}
    assert data["graduation_banner"]["kind"] in ("NOT_OPEN", "OPEN", "AFTER_PROGRAM_END", "CLOSED", "TOO_EARLY")


def test_opt_selection_post_completion(client):
    body = {"opt_intent": "AFTER_GRADUATION", "first_time_at_level": True}
    assert client.put("/api/me/opt-selection", json=body, headers=AUTH).json()["opt_type"] == "POST_COMPLETION"


def test_opt_selection_while_studying_is_out_of_scope(client):
    body = {"opt_intent": "WHILE_STUDYING", "first_time_at_level": True}
    resp = client.put("/api/me/opt-selection", json=body, headers=AUTH)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "out_of_scope"


def test_opt_selection_not_first_time_is_out_of_scope(client):
    body = {"opt_intent": "AFTER_GRADUATION", "first_time_at_level": False}
    assert client.put("/api/me/opt-selection", json=body, headers=AUTH).status_code == 422


def test_status_i20_received_requires_dso_rec_date(client):
    resp = client.put("/api/me/status", json={"stage": "I20_RECEIVED"}, headers=AUTH)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "missing_fields"
    assert "dso_rec_date" in resp.json()["error"]["message"]


def test_status_i765_filed_requires_receipt_and_start(client):
    resp = client.put("/api/me/status", json={"stage": "I765_FILED", "uscis_receipt_date": "2027-03-25"}, headers=AUTH)
    assert resp.status_code == 422
    assert "requested_start_date" in resp.json()["error"]["message"]


def test_status_ok(client):
    body = {"stage": "I20_RECEIVED", "dso_rec_date": "2027-03-20"}
    assert client.put("/api/me/status", json=body, headers=AUTH).json()["stage"] == "I20_RECEIVED"


def test_offer_requires_start_date_when_has_offer(client):
    body = {"has_offer": True, "premium_intent": "NO"}
    resp = client.put("/api/me/offer", json=body, headers=AUTH)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "missing_fields"


# --- Plan ---


def test_generate_plan_uses_date_engine(client):
    plan = client.post("/api/me/opt-plan/generate", headers=AUTH).json()
    assert [t["id"] for t in plan["tasks"]] == ["T01", "T02", "T03", "T04", "T05", "T06"]
    profile = demo_profile()
    expected = compute_timeline(
        TimelineInput(
            program_end=profile.program_end_date,
            today=date.today(),
            has_offer=True,
            offer_start=profile.offer.offer_start_date,
        ),
        demo_params(profile),
    )
    nodes = {n["id"]: n for n in plan["nodes"]}
    assert nodes["N3"]["date"] == expected.node("N3").date.isoformat()
    assert nodes["N4"]["due_type"] == "FEDERAL"


def test_get_plan(client):
    plan = client.get("/api/me/opt-plan", headers=AUTH).json()
    assert plan["status"] == "ACTIVE"
    assert {t["status"] for t in plan["tasks"]} <= {
        "NOT_STARTED", "IN_PROGRESS", "WAITING_EXTERNAL", "COMPLETED", "BLOCKED"
    }
    tasks = {t["id"]: t for t in plan["tasks"]}
    assert tasks["T05"]["status"] == "BLOCKED"  # T03 not done yet


# --- Tasks ---


def test_task_detail(client):
    task = client.get("/api/me/tasks/T04", headers=AUTH).json()
    assert task["task"]["id"] == "T04"
    assert task["template_content"]["documents"]
    assert task["sources"]


def test_unknown_task_404(client):
    assert client.get("/api/me/tasks/T99", headers=AUTH).status_code == 404


def test_t03_complete_requires_dso_rec_date(client):
    resp = client.patch("/api/me/tasks/T03", json={"status": "COMPLETED"}, headers=AUTH)
    assert resp.status_code == 422
    assert "dso_rec_date" in resp.json()["error"]["message"]


def test_t03_complete_with_date(client):
    body = {"status": "COMPLETED", "dso_rec_date": "2027-03-20"}
    data = client.patch("/api/me/tasks/T03", json=body, headers=AUTH).json()
    assert data["task"]["status"] == "COMPLETED"
    assert data["plan_version"] >= 1


# --- Assistant and drafts ---


def test_assistant_refuses_out_of_scope(client):
    body = {"message": "How does the H-1B lottery work?", "current_page": "checklist"}
    data = client.post("/api/assistant/messages", json=body, headers=AUTH).json()
    assert data["scope"] == "OUT"
    assert "only help with OPT" in data["answer"]


def test_assistant_answers_in_users_language(client):
    body = {"message": "我下一步该做什么？", "current_page": "checklist"}
    data = client.post("/api/assistant/messages", json=body, headers=AUTH).json()
    assert data["language"] == "zh"
    assert data["intent"] == "NEXT_STEP"


def test_dso_draft(client):
    body = {"question_type": "CONFIRM_DATES", "user_question": "When is my deadline?", "current_task_id": "T05"}
    draft = client.post("/api/me/dso-drafts", json=body, headers=AUTH).json()
    assert draft["subject"]
    assert "[YOUR FULL NAME]" in draft["body"]
    assert "YOUR STUDENT ID" in draft["placeholders"]
