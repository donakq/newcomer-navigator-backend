import pytest
from fastapi.testclient import TestClient

from app.main import app

USER_ID = "3f6c1a2e-8b4d-4c5e-9a7f-1d2e3f4a5b6c"
H = {"X-User-Id": USER_ID}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def fresh_store():
    from app.services.store import reset_store

    reset_store()


@pytest.fixture(autouse=True)
def fresh_sessions():
    from app.mock import session_store

    session_store.reset()


@pytest.fixture
def auth(client):
    """Log in as a new user and load the demo student (PRD persona A) as their profile."""
    from app.mock import session_store
    from app.mock.opt_demo import demo_profile

    body = {"email": "demo@uw.edu", "code": "000000", "tos_accepted": True}
    token = client.post("/api/auth/email/verify", json=body).json()["token"]
    session_store.state_for(token).profile = demo_profile()
    return {"Authorization": f"Bearer {token}"}
