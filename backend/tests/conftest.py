import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


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
