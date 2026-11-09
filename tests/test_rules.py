from app.catalog_loader import get_catalog
from app.schemas.profile import Profile
from app.services.rules import evaluate, recommend, visible_steps


def by_id(recs):
    return {r.task_id: r for r in recs}


def test_eq_none_never_matches():
    cond = {"field": "has_ssn", "eq": False}
    assert evaluate(cond, {"has_ssn": None}) is False
    assert evaluate(cond, {}) is False


def test_in_none_never_matches():
    assert evaluate({"field": "job_type", "in": ["CPT", None]}, {"job_type": None}) is False


def test_all():
    cond = {"all": [{"field": "in_us", "eq": True}, {"field": "has_ssn", "eq": False}]}
    assert evaluate(cond, {"in_us": True, "has_ssn": False}) is True
    assert evaluate(cond, {"in_us": True, "has_ssn": True}) is False


def test_any():
    cond = {"any": [{"field": "in_us", "eq": True}, {"field": "has_ssn", "eq": False}]}
    assert evaluate(cond, {"in_us": False, "has_ssn": False}) is True
    assert evaluate(cond, {"in_us": False, "has_ssn": True}) is False


def test_not():
    assert evaluate({"not": {"field": "in_us", "eq": True}}, {"in_us": False}) is True


def test_new_arrival_gets_phone_and_bank():
    profile = Profile(in_us=True, has_us_phone=False, has_bank_account=False)
    recs = recommend(profile, get_catalog())
    assert [r.task_id for r in recs] == ["bank_account", "us_phone"]
    assert by_id(recs)["bank_account"].blocked_by == ["us_phone"]


def test_blocked_by_clears_when_dependency_done():
    profile = Profile(in_us=True, has_us_phone=False, has_bank_account=False)
    recs = recommend(profile, get_catalog(), done_task_ids={"us_phone"})
    assert by_id(recs)["bank_account"].blocked_by == []


def test_job_offer_without_ssn_gets_ssn():
    recs = by_id(recommend(Profile(has_ssn=False, has_job_offer=True), get_catalog()))
    assert recs["ssn"].reason == get_catalog().tasks["ssn"].reason


def test_unknown_ssn_status_gets_no_ssn_task():
    recs = by_id(recommend(Profile(has_job_offer=True), get_catalog()))
    assert "ssn" not in recs


def test_cpt_step_only_for_cpt():
    ssn = get_catalog().tasks["ssn"]
    assert [s.id for s in visible_steps(ssn, Profile(job_type="CPT"))][0] == "cpt_authorization"
    assert "cpt_authorization" not in [s.id for s in visible_steps(ssn, Profile(job_type="on_campus"))]
