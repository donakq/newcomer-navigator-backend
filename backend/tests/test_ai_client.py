import pytest

from app.ai import client as llm


def test_complete_without_key_raises(monkeypatch):
    monkeypatch.setattr(llm.config, "LLM_API_KEY", "")
    with pytest.raises(llm.LLMUnavailable):
        llm.complete("s", "u")
