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

    Uses config.LLM_PROVIDER. Raises LLMUnavailable on a missing key, an unknown provider, an API error,
    a refusal or an unparseable reply, so callers have one failure to fall back from.
    """
    if config.LLM_PROVIDER == "gemini":
        return _parse_gemini(system, user, output_format, model)
    if config.LLM_PROVIDER != "anthropic":
        raise LLMUnavailable(f"unknown LLM_PROVIDER {config.LLM_PROVIDER!r}")
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


def _gemini_client():
    """google-genai 3.x client; imported here so an Anthropic-only deployment never loads it."""
    from google import genai
    from google.genai import types

    return genai.Client(api_key=config.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=20_000))  # ms


def _parse_gemini(system: str, user: str, output_format: type[T], model: str | None) -> T:
    from google.genai import errors, types
    from pydantic import ValidationError

    if not config.GEMINI_API_KEY:
        raise LLMUnavailable("GEMINI_API_KEY is not set")
    client = _gemini_client()
    try:
        response = client.models.generate_content(
            model=model or config.GEMINI_MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_json_schema=output_format.model_json_schema(),
            ),
        )
    except errors.APIError as e:  # quota (429), bad key, server errors
        raise LLMUnavailable(str(e)) from e
    try:
        return output_format.model_validate_json(response.text or "")
    except ValidationError as e:
        raise LLMUnavailable(f"unparseable Gemini output: {e}") from e


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
