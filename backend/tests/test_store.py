"""Storage behavior: persistence, all-or-nothing saves, sessions."""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.mock.opt_demo import demo_profile
from app.schemas.opt import ProcessingChoice, TaskStatus
from app.store.sql import Base, SessionRow, SqlStore


def test_data_survives_restart(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'app.db'}"
    first = SqlStore(url)
    token, _ = first.login("persist@uw.edu", "America/Los_Angeles")
    state = first.state_for(token)
    state.profile = demo_profile().model_copy(update={"processing": ProcessingChoice(uscis_standard_days=120)})
    state.task_statuses = {"T01": TaskStatus.COMPLETED}
    first.save(state)
    first.engine.dispose()

    restarted = SqlStore(url)  # a new process, same database
    again = restarted.state_for(token)
    assert again.profile.program_end_date == date(2027, 6, 11)
    assert again.profile.offer.offer_start_date == date(2027, 7, 12)
    assert again.task_statuses == {"T01": TaskStatus.COMPLETED}
    assert again.profile.processing.uscis_standard_days == 120


def test_rejected_request_saves_nothing(client, auth):
    bad = {"has_offer": False, "start_preference": "SPECIFIC_DATE", "preferred_start_date": "2027-01-01",
           "premium_intent": "NO"}
    assert client.put("/api/me/offer", json=bad, headers=auth).status_code == 422
    offer = client.get("/api/me/profile", headers=auth).json()["profile"]["offer"]
    assert offer["has_offer"] is True  # the demo student's saved offer is untouched


def test_expired_session_is_rejected(store):
    if not isinstance(store, SqlStore):
        pytest.skip("expiry is stored in the database")
    token, _ = store.login("old@uw.edu", "America/Los_Angeles")
    with Session(store.engine) as db, db.begin():
        db.execute(update(SessionRow).values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    assert store.state_for(token) is None


def test_delete_user_removes_every_row(store):
    if not isinstance(store, SqlStore):
        pytest.skip("checks database tables")
    token, _ = store.login("bye@uw.edu", "America/Los_Angeles")
    state = store.state_for(token)
    state.profile = demo_profile().model_copy(update={"processing": ProcessingChoice(school_business_days=20)})
    state.task_statuses = {"T01": TaskStatus.COMPLETED}
    store.save(state)
    store.delete_user(token)
    with Session(store.engine) as db:
        for table in Base.metadata.sorted_tables:
            assert db.scalar(select(func.count()).select_from(table)) == 0, table.name


def test_login_is_case_insensitive(store):
    _, first = store.login("Mixed@UW.edu", "America/Los_Angeles")
    _, second = store.login("mixed@uw.edu", "America/Los_Angeles")
    assert (first, second) == (True, False)


def test_only_token_hash_is_stored(store):
    if not isinstance(store, SqlStore):
        pytest.skip("checks database tables")
    token, _ = store.login("hash@uw.edu", "America/Los_Angeles")
    with Session(store.engine) as db:
        stored = db.scalar(select(SessionRow.token_hash))
    assert stored != token and len(stored) == 64
