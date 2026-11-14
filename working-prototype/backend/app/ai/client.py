"""The one door to Azure OpenAI: the Responses API for written drafts and the Decisions
API for typed answers. Both run on `gpt-6-luna` by default.

Keys are sent in a header and never logged; errors are reported by kind only.
"""

import json
import logging
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger("datalens.ai")
TIMEOUT = httpx.Timeout(45.0, connect=10.0)
_transport: httpx.BaseTransport | None = None


class AiUnavailable(Exception):
    """The AI service could not give a usable answer; the caller falls back to people."""


def set_transport(transport: httpx.BaseTransport | None) -> None:
    """Swap the HTTP transport (tests use a mock transport)."""
    global _transport
    _transport = transport


def ai_available() -> bool:
    return bool(settings.azure_openai_endpoint and settings.azure_openai_api_key)


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    if not ai_available():
        raise AiUnavailable("not configured")
    base = settings.azure_v1_base
    headers = {"api-key": settings.azure_openai_api_key or "", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=TIMEOUT, transport=_transport) as http:
            response = http.post(f"{base}/{path}", headers=headers, json=body)
    except httpx.HTTPError as error:
        log.warning("AI call to %s failed: %s", path, type(error).__name__)
        raise AiUnavailable(type(error).__name__) from None
    if response.status_code != 200:
        log.warning("AI call to %s returned status %s", path, response.status_code)
        raise AiUnavailable(f"status {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise AiUnavailable("response was not JSON") from None


def respond_json(
    instructions: str, prompt: str, schema: dict[str, Any], name: str
) -> dict[str, Any]:
    """Ask for a written draft as JSON matching `schema`."""
    body = {
        "model": settings.ai_text_model,
        "instructions": instructions,
        "input": prompt,
        "text": {"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}},
    }
    data = _post("responses", body)
    texts = [
        part.get("text", "")
        for item in data.get("output", [])
        for part in item.get("content", []) or []
        if part.get("type") == "output_text"
    ]
    if not texts:
        raise AiUnavailable("no text in the response")
    try:
        parsed = json.loads(texts[0])
    except ValueError:
        raise AiUnavailable("draft was not valid JSON") from None
    if not isinstance(parsed, dict):
        raise AiUnavailable("draft was not an object")
    return parsed


def decisions(input_value: Any, questions: list[dict[str, Any]]) -> dict[str, Any]:
    body = {"model": settings.ai_decisions_model, "input": input_value, "questions": questions}
    return _post("decisions", body)
