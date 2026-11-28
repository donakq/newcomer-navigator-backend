"""LLM_PROVIDER switch in app.ai.client. The Gemini SDK is faked; no test calls a real API."""

import pytest
from google.genai import errors
from pydantic import BaseModel

from app import config
from app.ai import client
from app.ai.client import LLMUnavailable


class Label(BaseModel):
    scope: str
    confidence: float


class FakeGemini:
    """Stands in for google.genai.Client: records the call and returns `text`."""

    def __init__(self, text='{"scope": "IN", "confidence": 0.9}', error: Exception | None = None):
        self.text, self.error, self.calls = text, error, []
        self.models = self

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        return type("Response", (), {"text": self.text})()


@pytest.fixture
def gemini(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    fake = FakeGemini()
    monkeypatch.setattr(client, "_gemini_client", lambda: fake)
    return fake


def test_gemini_returns_the_validated_model(gemini):
    assert client.parse("SYSTEM", "hello", Label) == Label(scope="IN", confidence=0.9)


def test_gemini_gets_system_prompt_schema_and_model(gemini):
    client.parse("SYSTEM", "hello", Label)
    call = gemini.calls[0]
    assert call["model"] == config.GEMINI_MODEL
    assert call["contents"] == "hello"
    assert call["config"].system_instruction == "SYSTEM"
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_json_schema == Label.model_json_schema()


def test_gemini_invalid_json_falls_back(gemini):
    gemini.text = "not json"
    with pytest.raises(LLMUnavailable):
        client.parse("SYSTEM", "hello", Label)


def test_gemini_api_error_falls_back(gemini):
    gemini.error = errors.APIError(429, {"error": {"message": "quota exceeded"}})
    with pytest.raises(LLMUnavailable):
        client.parse("SYSTEM", "hello", Label)


def test_gemini_without_key_falls_back(gemini, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with pytest.raises(LLMUnavailable):
        client.parse("SYSTEM", "hello", Label)


def test_unknown_provider_falls_back(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "nope")
    with pytest.raises(LLMUnavailable):
        client.parse("SYSTEM", "hello", Label)


def test_default_provider_is_anthropic():
    assert config.LLM_PROVIDER == "anthropic"
