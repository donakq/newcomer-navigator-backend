from uuid import UUID

import pytest

from app.ai import client as llm
from app.services.chat import CHAT_FALLBACK
from app.services.store import get_store
from tests.conftest import H, USER_ID


@pytest.fixture
def llm_reply(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda system, user, **kw: "hi")


@pytest.fixture
def llm_down(monkeypatch):
    def fail(system, user, **kw):
        raise llm.LLMUnavailable("no key")

    monkeypatch.setattr(llm, "complete", fail)


def test_chat_uses_llm_reply(client, llm_reply):
    resp = client.post("/api/chat", json={"message": "hello"}, headers=H)
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "hi"
    assert body["detected_events"] == []
    assert body["checklist_diff"] is None
    assert body["citations"] == []
    messages = get_store().get_messages(UUID(USER_ID))
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_chat_falls_back_without_llm(client, llm_down):
    resp = client.post("/api/chat", json={"message": "hello"}, headers=H)
    assert resp.status_code == 200
    assert resp.json()["reply"] == CHAT_FALLBACK


def test_chat_empty_message_422(client, llm_reply):
    assert client.post("/api/chat", json={"message": ""}, headers=H).status_code == 422


def test_chat_too_long_422(client, llm_reply):
    assert client.post("/api/chat", json={"message": "x" * 2001}, headers=H).status_code == 422


def test_complete_without_key_raises(monkeypatch):
    monkeypatch.setattr(llm.config, "LLM_API_KEY", "")
    with pytest.raises(llm.LLMUnavailable):
        llm.complete("s", "u")


def test_dso_draft_template(client):
    resp = client.post("/api/tasks/ssn/steps/dso_letter/dso-draft", json={}, headers=H)
    assert resp.status_code == 200
    draft = resp.json()
    assert "Apply for a Social Security Number" in draft["subject"]
    assert draft["placeholders"] == ["YOUR FULL NAME", "YOUR SEVIS ID"]
    assert "[YOUR SEVIS ID]" in draft["body"]
    assert draft["bring_list"] == ["I-20", "Job offer letter"]


def test_dso_draft_includes_question(client):
    q = "Can I apply before my job starts?"
    draft = client.post(
        "/api/tasks/ssn/steps/dso_letter/dso-draft", json={"question": q}, headers=H
    ).json()
    assert draft["questions"][0] == q
    assert q in draft["body"]


def test_dso_draft_unknown_step_404(client):
    resp = client.post("/api/tasks/ssn/steps/nope/dso-draft", json={}, headers=H)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
