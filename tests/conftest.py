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
