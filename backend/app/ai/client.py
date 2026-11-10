"""The only module that talks to the LLM API."""

import anthropic

from app import config


class LLMUnavailable(Exception):
    """No API key, or the LLM call failed. Callers fall back to non-AI behavior."""


def complete(system: str, user: str, model: str | None = None, max_tokens: int = 512) -> str:
    if not config.LLM_API_KEY:
        raise LLMUnavailable("LLM_API_KEY is not set")
    client = anthropic.Anthropic(api_key=config.LLM_API_KEY, timeout=20.0, max_retries=1)
    try:
        response = client.messages.create(
            model=model or config.FAST_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APIError as e:
        raise LLMUnavailable(str(e)) from e
    text = "".join(block.text for block in response.content if block.type == "text")
    if not text:
        raise LLMUnavailable("empty response")
    return text
