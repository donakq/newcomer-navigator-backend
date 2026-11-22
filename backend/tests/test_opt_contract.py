"""API contract for OPT MVP v1 (PRD v1.3 section 8.3), served from mock data."""

from datetime import date

from app.opt.timeline import TimelineInput, compute_timeline
from app.mock.opt_demo import demo_params, demo_profile



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


def test_logout(client, auth):
    assert client.post("/api/auth/logout", headers=auth).status_code == 204


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


def test_onboarding(client, auth):
    body = {"school_id": "uw", "program_end_date": "2027-06-11", "degree_level": "MASTER"}
    profile = client.put("/api/me/onboarding", json=body, headers=auth).json()["profile"]
    assert profile["program_end_date"] == "2027-06-11"


def test_onboarding_unsupported_school_409(client, auth):
    body = {"school_id": "other", "program_end_date": "2027-06-11", "degree_level": "MASTER"}
    resp = client.put("/api/me/onboarding", json=body, headers=auth)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "unsupported_school"


def test_onboarding_requires_program_end_date(client, auth):
    body = {"school_id": "uw", "degree_level": "MASTER"}
    assert client.put("/api/me/onboarding", json=body, headers=auth).status_code == 422


def test_get_profile(client, auth):
    data = client.get("/api/me/profile", headers=auth).json()["profile"]
    assert data["school"]["id"] == "uw"
    assert data["stage"] == "PLANNING"
    assert data["offer"]["has_offer"] is True


def test_patch_profile_returns_plan_version(client, auth):
    resp = client.patch("/api/me/profile", json={"program_end_date": "2027-06-20"}, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["plan_version"] >= 1


def test_delete_account(client, auth):
    assert client.delete("/api/me", headers=auth).status_code == 204


# --- Checklist, Select OPT, Status, Offer ---


def test_checklist_modules(client, auth):
    data = client.get("/api/me/checklist", headers=auth).json()
    statuses = {m["id"]: m["status"] for m in data["modules"]}
    assert statuses["work_authorization"] == "OPEN"
    assert set(statuses.values()) == {"OPEN", "COMING_SOON"}
    assert data["graduation_banner"]["kind"] in ("NOT_OPEN", "OPEN", "AFTER_PROGRAM_END", "CLOSED", "TOO_EARLY")


def test_opt_selection_post_completion(client, auth):
    body = {"opt_intent": "AFTER_GRADUATION", "first_time_at_level": True}
    assert client.put("/api/me/opt-selection", json=body, headers=auth).json()["opt_type"] == "POST_COMPLETION"


def test_opt_selection_while_studying_is_out_of_scope(client, auth):
    body = {"opt_intent": "WHILE_STUDYING", "first_time_at_level": True}
    resp = client.put("/api/me/opt-selection", json=body, headers=auth)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "out_of_scope"


def test_opt_selection_not_first_time_is_out_of_scope(client, auth):
    body = {"opt_intent": "AFTER_GRADUATION", "first_time_at_level": False}
    assert client.put("/api/me/opt-selection", json=body, headers=auth).status_code == 422


def test_status_i20_received_requires_dso_rec_date(client, auth):
    resp = client.put("/api/me/status", json={"stage": "I20_RECEIVED"}, headers=auth)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "missing_fields"
    assert "dso_rec_date" in resp.json()["error"]["message"]


def test_status_i765_filed_requires_receipt_and_start(client, auth):
    resp = client.put("/api/me/status", json={"stage": "I765_FILED", "uscis_receipt_date": "2027-03-25"}, headers=auth)
    assert resp.status_code == 422
    assert "requested_start_date" in resp.json()["error"]["message"]


def test_status_ok(client, auth):
    body = {"stage": "I20_RECEIVED", "dso_rec_date": "2027-03-20"}
    assert client.put("/api/me/status", json=body, headers=auth).json()["stage"] == "I20_RECEIVED"


def test_offer_requires_start_date_when_has_offer(client, auth):
    body = {"has_offer": True, "premium_intent": "NO"}
    resp = client.put("/api/me/offer", json=body, headers=auth)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "missing_fields"


# --- Plan ---


def test_generate_plan_uses_date_engine(client, auth):
    plan = client.post("/api/me/opt-plan/generate", headers=auth).json()
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


def test_get_plan(client, auth):
    plan = client.get("/api/me/opt-plan", headers=auth).json()
    assert plan["status"] == "ACTIVE"
    assert {t["status"] for t in plan["tasks"]} <= {
        "NOT_STARTED", "IN_PROGRESS", "WAITING_EXTERNAL", "COMPLETED", "BLOCKED"
    }
    tasks = {t["id"]: t for t in plan["tasks"]}
    assert tasks["T05"]["status"] == "BLOCKED"  # T03 not done yet


# --- Tasks ---


def test_task_detail(client, auth):
    task = client.get("/api/me/tasks/T04", headers=auth).json()
    assert task["task"]["id"] == "T04"
    assert task["template_content"]["documents"]
    assert task["sources"]


def test_unknown_task_404(client, auth):
    assert client.get("/api/me/tasks/T99", headers=auth).status_code == 404


def submit_t02(client, auth):
    client.patch("/api/me/tasks/T02", json={"status": "WAITING_EXTERNAL", "i20_request_date": "2027-03-01"}, headers=auth)


def test_t03_blocked_until_t02_submitted(client, auth):
    resp = client.patch("/api/me/tasks/T03", json={"status": "IN_PROGRESS"}, headers=auth)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "task_blocked"


def test_t03_complete_requires_dso_rec_date(client, auth):
    submit_t02(client, auth)
    resp = client.patch("/api/me/tasks/T03", json={"status": "COMPLETED"}, headers=auth)
    assert resp.status_code == 422
    assert "dso_rec_date" in resp.json()["error"]["message"]


def test_t03_complete_with_date(client, auth):
    submit_t02(client, auth)
    body = {"status": "COMPLETED", "dso_rec_date": "2027-03-20"}
    data = client.patch("/api/me/tasks/T03", json=body, headers=auth).json()
    assert data["task"]["status"] == "COMPLETED"
    assert data["plan_version"] >= 1


# --- Assistant and drafts ---


def test_assistant_refuses_out_of_scope(client, auth):
    body = {"message": "How does the H-1B lottery work?", "current_page": "checklist"}
    data = client.post("/api/assistant/messages", json=body, headers=auth).json()
    assert data["scope"] == "OUT"
    assert "only help with OPT" in data["answer"]


def test_assistant_answers_in_users_language(client, auth):
    body = {"message": "我下一步该做什么？", "current_page": "checklist"}
    data = client.post("/api/assistant/messages", json=body, headers=auth).json()
    assert data["language"] == "zh"
    assert data["intent"] == "NEXT_STEP"


def test_dso_draft(client, auth):
    body = {"question_type": "CONFIRM_DATES", "user_question": "When is my deadline?", "current_task_id": "T05"}
    draft = client.post("/api/me/dso-drafts", json=body, headers=auth).json()
    assert draft["subject"]
    assert "[YOUR FULL NAME]" in draft["body"]
    assert "YOUR STUDENT ID" in draft["placeholders"]


# --- Per-user state (mock store) ---


def login(client, email="new@uw.edu"):
    body = {"email": email, "code": "000000", "tos_accepted": True}
    data = client.post("/api/auth/email/verify", json=body).json()
    return {"Authorization": f"Bearer {data['token']}"}, data["is_new_user"]


def test_unknown_token_is_unauthenticated(client):
    resp = client.get("/api/me/profile", headers={"Authorization": "Bearer not-a-session"})
    assert resp.status_code == 401


def test_new_user_must_onboard_first(client):
    headers, is_new = login(client)
    assert is_new is True
    resp = client.get("/api/me/profile", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "onboarding_required"


def test_full_flow_is_saved_per_user(client):
    headers, _ = login(client)
    client.put("/api/me/onboarding", json={"school_id": "uw", "program_end_date": "2027-06-11",
                                          "degree_level": "MASTER"}, headers=headers)
    client.put("/api/me/opt-selection", json={"opt_intent": "AFTER_GRADUATION", "first_time_at_level": True},
               headers=headers)
    client.put("/api/me/status", json={"stage": "I20_RECEIVED", "dso_rec_date": "2027-03-20"}, headers=headers)
    client.put("/api/me/offer", json={"has_offer": True, "offer_start_date": "2027-07-12",
                                     "premium_intent": "NO"}, headers=headers)
    plan = client.get("/api/me/opt-plan", headers=headers).json()
    tasks = {t["id"]: t["status"] for t in plan["tasks"]}
    assert tasks["T01"] == "COMPLETED"  # done by Select OPT
    assert tasks["T03"] == "COMPLETED"  # done by the I20_RECEIVED stage
    assert tasks["T05"] == "NOT_STARTED"  # unblocked now
    nodes = {n["id"]: n for n in plan["nodes"]}
    assert nodes["N4"]["date"] == "2027-04-19"  # min(P + 60, R + 30) with the saved R


def test_users_do_not_see_each_others_data(client):
    a, _ = login(client, "a@uw.edu")
    b, _ = login(client, "b@uw.edu")
    client.put("/api/me/onboarding", json={"school_id": "uw", "program_end_date": "2027-06-11",
                                          "degree_level": "MASTER"}, headers=a)
    assert client.get("/api/me/profile", headers=b).status_code == 404


def test_returning_user_keeps_data(client):
    first, _ = login(client, "back@uw.edu")
    client.put("/api/me/onboarding", json={"school_id": "uw", "program_end_date": "2027-06-11",
                                          "degree_level": "PHD"}, headers=first)
    again, is_new = login(client, "back@uw.edu")
    assert is_new is False
    assert client.get("/api/me/profile", headers=again).json()["profile"]["degree_level"] == "PHD"


def test_delete_account_removes_data_and_session(client):
    headers, _ = login(client, "gone@uw.edu")
    client.put("/api/me/onboarding", json={"school_id": "uw", "program_end_date": "2027-06-11",
                                          "degree_level": "MASTER"}, headers=headers)
    assert client.delete("/api/me", headers=headers).status_code == 204
    assert client.get("/api/me/profile", headers=headers).status_code == 401


def test_recording_a_date_on_a_task_applies_that_stage(client):
    headers, _ = login(client, "stage@uw.edu")
    client.put("/api/me/onboarding", json={"school_id": "uw", "program_end_date": "2027-06-11",
                                          "degree_level": "MASTER"}, headers=headers)
    client.put("/api/me/opt-selection", json={"opt_intent": "AFTER_GRADUATION", "first_time_at_level": True},
               headers=headers)
    client.patch("/api/me/tasks/T02", json={"status": "WAITING_EXTERNAL", "i20_request_date": "2027-03-01"},
                 headers=headers)
    client.patch("/api/me/tasks/T03", json={"status": "COMPLETED", "dso_rec_date": "2027-03-20"}, headers=headers)
    tasks = {t["id"]: t["status"] for t in client.get("/api/me/opt-plan", headers=headers).json()["tasks"]}
    assert tasks["T02"] == "COMPLETED"  # the OPT I-20 arrived, so the request is done


# --- Processing times the student picks (reviewed UW policy, 2026-11-16) ---


def test_plan_shows_processing_ranges_with_conservative_defaults(client, auth):
    plan = client.get("/api/me/opt-plan", headers=auth).json()
    times = {p["id"]: p for p in plan["processing"]}
    assert (times["uscis_standard_days"]["min"], times["uscis_standard_days"]["max"]) == (90, 150)
    assert times["uscis_standard_days"]["used"] == 150 and times["uscis_standard_days"]["chosen"] is None
    assert times["school_business_days"]["unit"] == "business_days"
    assert times["uscis_premium_business_days"]["used"] == 30


def test_student_picks_processing_time_and_plan_follows(client, auth):
    before = {n["id"]: n for n in client.get("/api/me/opt-plan", headers=auth).json()["nodes"]}
    resp = client.put("/api/me/processing-times", json={"uscis_standard_days": 90}, headers=auth)
    assert resp.status_code == 200
    plan = client.get("/api/me/opt-plan", headers=auth).json()
    after = {n["id"]: n for n in plan["nodes"]}
    assert {p["id"]: p["used"] for p in plan["processing"]}["uscis_standard_days"] == 90
    assert after["N3"]["date"] > before["N3"]["date"]  # shorter wait -> file later


def test_processing_time_outside_range_rejected(client, auth):
    resp = client.put("/api/me/processing-times", json={"school_business_days": 10}, headers=auth)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "out_of_range"


def test_plan_has_uw_school_request_deadline(client, auth):
    nodes = {n["id"]: n for n in client.get("/api/me/opt-plan", headers=auth).json()["nodes"]}
    assert nodes["N1d"]["date"] == "2027-07-21"  # P + 40
    tasks = {t["id"]: t for t in client.get("/api/me/opt-plan", headers=auth).json()["tasks"]}
    assert tasks["T02"]["deadline_at"] == "2027-07-21"


def test_issue_date_only_flags_unconfirmed_sevis_date(client, auth):
    client.put("/api/me/status", json={"stage": "I20_REQUESTED", "i20_issue_date": "2027-03-20"}, headers=auth)
    plan = client.get("/api/me/opt-plan", headers=auth).json()
    assert "SEVIS_DATE_UNCONFIRMED" in plan["risk_labels"]


def test_office_has_reviewed_contact_details(client):
    office = client.get("/api/schools/uw/office").json()
    assert office["preferred_channel"] == "FORM"
    assert office["advising_form_url"] == "https://iss.washington.edu/email/"
    assert "3–5 business days" in office["notes"]
