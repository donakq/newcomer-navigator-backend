"""The only module that talks to the LLM API."""

from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app import config

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(Exception):
    """No API key, or the LLM call failed. Callers fall back to non-AI behavior."""


def _client() -> anthropic.Anthropic:
    if not config.LLM_API_KEY:
        raise LLMUnavailable("LLM_API_KEY is not set")
    return anthropic.Anthropic(api_key=config.LLM_API_KEY, timeout=20.0, max_retries=1)


def parse(system: str, user: str, output_format: type[T], model: str | None = None, max_tokens: int = 4096) -> T:
    """Structured output: the reply is validated against the Pydantic model `output_format`.

    Raises LLMUnavailable on a missing key, an API error, a refusal or an unparseable reply,
    so callers have one failure to fall back from.
    """
    client = _client()
    try:
        response = client.messages.parse(
            model=model or config.FAST_MODEL,
            max_tokens=max_tokens,
            # The system prompt is a fixed prefix: cache it (prefixes under the model's minimum just don't cache).
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_format=output_format,
        )
    except (anthropic.APIError, ValueError) as e:
        raise LLMUnavailable(str(e)) from e
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise LLMUnavailable(f"no usable output (stop_reason={response.stop_reason})")
    return response.parsed_output


def complete(system: str, user: str, model: str | None = None, max_tokens: int = 512) -> str:
    client = _client()
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
