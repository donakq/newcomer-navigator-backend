"""Date ranges on the plan: legal filing window, EAD estimate, and dates still missing (design 2026-11-27).

The `auth` fixture loads demo_profile(): P 2027-06-11, offer start 2027-07-12, stage PLANNING, no R.
"""

from datetime import date, timedelta

from app.opt.business_days import add_business_days

OFFER = {"has_offer": True, "offer_start_date": "2027-07-12", "start_flexible": "NOT_SURE", "premium_intent": "NO"}


def _plan(client, auth):
    return client.get("/api/me/opt-plan", headers=auth).json()


def _ranges(plan):
    return {r["id"]: r for r in plan["ranges"]}


def _node(plan, node_id):
    return date.fromisoformat(next(n for n in plan["nodes"] if n["id"] == node_id)["date"])


def _status(client, auth, **body):
    assert client.put("/api/me/status", json=body, headers=auth).status_code == 200


def _offer(client, auth, **body):
    assert client.put("/api/me/offer", json=body, headers=auth).status_code == 200


def test_demo_student_gets_window_ead_and_dso_ranges(client, auth):
    plan = _plan(client, auth)
    r = _ranges(plan)
    assert set(r) == {"FILING_WINDOW", "EAD_ARRIVAL", "DSO_REC_DATE"}
    assert r["FILING_WINDOW"]["kind"] == "LEGAL_WINDOW"
    assert r["FILING_WINDOW"]["action"] == "CONFIRM_WITH_SCHOOL"
    assert (r["FILING_WINDOW"]["start"], r["FILING_WINDOW"]["end"]) == (str(_node(plan, "N2")), str(_node(plan, "N4")))
    n3 = _node(plan, "N3")
    assert r["EAD_ARRIVAL"]["kind"] == "ESTIMATE"
    assert (r["EAD_ARRIVAL"]["start"], r["EAD_ARRIVAL"]["end"]) == (str(n3 + timedelta(90)), str(n3 + timedelta(150)))
    n1 = _node(plan, "N1")
    assert r["DSO_REC_DATE"]["kind"] == "NEEDS_DATE"
    assert r["DSO_REC_DATE"]["start"] == str(add_business_days(n1, 20))
    assert r["DSO_REC_DATE"]["end"] == str(add_business_days(n1, 28))
    assert [x["start"] for x in plan["ranges"]] == sorted(x["start"] for x in plan["ranges"])


def test_dso_range_gone_once_r_known(client, auth):
    _status(client, auth, stage="I20_RECEIVED", dso_rec_date="2027-03-20")
    r = _ranges(_plan(client, auth))
    assert "DSO_REC_DATE" not in r
    assert (r["FILING_WINDOW"]["start"], r["FILING_WINDOW"]["end"]) == ("2027-03-20", "2027-04-19")


def test_premium_uses_business_day_range(client, auth):
    _offer(client, auth, **{**OFFER, "premium_intent": "YES"})
    plan = _plan(client, auth)
    n3 = _node(plan, "N3")
    ead = _ranges(plan)["EAD_ARRIVAL"]
    assert (ead["start"], ead["end"]) == (str(add_business_days(n3, 1)), str(add_business_days(n3, 30)))


def test_after_filing_no_window_and_ead_from_receipt(client, auth):
    _status(client, auth, stage="I765_FILED", dso_rec_date="2027-03-20", uscis_receipt_date="2027-03-25",
            requested_start_date="2027-07-12")
    r = _ranges(_plan(client, auth))
    assert "FILING_WINDOW" not in r
    assert "DSO_REC_DATE" not in r
    assert r["EAD_ARRIVAL"]["start"] == "2027-06-23"


def test_approved_has_no_ead_range(client, auth):
    _status(client, auth, stage="APPROVED", dso_rec_date="2027-03-20", uscis_receipt_date="2027-03-25",
            requested_start_date="2027-07-12")
    assert "EAD_ARRIVAL" not in _ranges(_plan(client, auth))


def test_no_offer_not_sure_gets_start_date_range(client, auth):
    _offer(client, auth, has_offer=False, start_preference="NOT_SURE", premium_intent="NO")
    start = _ranges(_plan(client, auth))["START_DATE"]
    assert start["kind"] == "NEEDS_DATE"
    assert start["action"] == "PICK_START_DATE"
    assert (start["start"], start["end"]) == ("2027-06-12", "2027-08-10")


def test_conflict_has_no_ranges(client, auth):
    _status(client, auth, stage="I20_RECEIVED", dso_rec_date="2027-02-01")  # R + 30 < P - 90
    assert _plan(client, auth)["ranges"] == []


def test_ead_range_ends_at_the_students_processing_time(client, auth):
    assert client.put("/api/me/processing-times", json={"uscis_standard_days": 100}, headers=auth).status_code == 200
    plan = _plan(client, auth)
    n3 = _node(plan, "N3")
    ead = _ranges(plan)["EAD_ARRIVAL"]
    assert (ead["start"], ead["end"]) == (str(n3 + timedelta(90)), str(n3 + timedelta(100)))
    assert "90–100 days" in ead["note"]


# --- Final-review fixes ---


def test_approved_without_dates_has_no_filing_window(client, auth):
    _status(client, auth, stage="APPROVED")
    r = _ranges(_plan(client, auth))
    assert "FILING_WINDOW" not in r and "EAD_ARRIVAL" not in r and "DSO_REC_DATE" not in r


def test_filed_stage_has_no_filing_window(client, auth):
    _status(client, auth, stage="I765_FILED", uscis_receipt_date="2027-03-25", requested_start_date="2027-07-12")
    assert "FILING_WINDOW" not in _ranges(_plan(client, auth))


def test_too_early_has_no_ranges(client, auth):
    _offer(client, auth, has_offer=False, start_preference="NOT_SURE", premium_intent="NO")
    assert client.patch("/api/me/profile", json={"program_end_date": "2028-06-01"}, headers=auth).status_code == 200
    plan = _plan(client, auth)
    assert plan["too_early"] is True
    assert plan["ranges"] == []


def test_window_closed_has_no_ranges(client, auth):
    _offer(client, auth, has_offer=False, start_preference="NOT_SURE", premium_intent="NO")
    assert client.patch("/api/me/profile", json={"program_end_date": "2026-06-01"}, headers=auth).status_code == 200
    plan = _plan(client, auth)
    assert "WINDOW_CLOSED" in plan["risk_labels"]
    assert plan["ranges"] == []


def test_conflict_hides_start_date_range_too(client, auth):
    _offer(client, auth, has_offer=False, start_preference="NOT_SURE", premium_intent="NO")
    _status(client, auth, stage="I20_RECEIVED", dso_rec_date="2027-02-01")
    assert _plan(client, auth)["ranges"] == []
