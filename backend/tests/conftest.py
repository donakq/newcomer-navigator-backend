import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import get_store, set_store
from app.store.memory import MemoryStore
from app.store.sql import Base, SqlStore

# Every test runs against both stores. Set TEST_DATABASE_URL to also run against a real Postgres.
STORES = ["memory", "sqlite"] + (["postgres"] if os.getenv("TEST_DATABASE_URL") else [])


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True, params=STORES)
def store(request):
    if request.param == "memory":
        s = MemoryStore()
    elif request.param == "sqlite":
        s = SqlStore("sqlite+pysqlite:///:memory:")
    else:
        s = SqlStore(os.environ["TEST_DATABASE_URL"])
        Base.metadata.drop_all(s.engine)
        Base.metadata.create_all(s.engine)
    set_store(s)
    yield s
    if isinstance(s, SqlStore):
        s.engine.dispose()


@pytest.fixture
def auth(client):
    """Log in as a new user and load the demo student (PRD persona A) as their profile."""
    from app.mock.opt_demo import demo_profile

    body = {"email": "demo@uw.edu", "code": "000000", "tos_accepted": True}
    token = client.post("/api/auth/email/verify", json=body).json()["token"]
    state = get_store().state_for(token)
    state.profile = demo_profile()
    get_store().save(state)
    return {"Authorization": f"Bearer {token}"}
