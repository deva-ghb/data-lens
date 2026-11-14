"""The JSON shape every written AI draft follows."""

from typing import Any

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "sure": {"type": "array", "items": {"type": "string"}},
        "unsure": {"type": "array", "items": {"type": "string"}},
        "would_change": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
        "reasoning": {
            "type": "object",
            "properties": {
                "evidence": {"type": "array", "items": {"type": "string"}},
                "rules": {"type": "array", "items": {"type": "string"}},
                "inferences": {"type": "array", "items": {"type": "string"}},
                "rejected": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["evidence", "rules", "inferences", "rejected"],
            "additionalProperties": False,
        },
    },
    "required": ["content", "sure", "unsure", "would_change", "confidence", "reasoning"],
    "additionalProperties": False,
}


def valid_draft(data: dict[str, Any]) -> bool:
    if not isinstance(data.get("content"), str) or not data["content"].strip():
        return False
    for key in ("sure", "unsure", "would_change"):
        if not isinstance(data.get(key), list):
            return False
    confidence = data.get("confidence")
    if not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
        return False
    reasoning = data.get("reasoning")
    return isinstance(reasoning, dict) and all(
        isinstance(reasoning.get(k), list) for k in ("evidence", "rules", "inferences", "rejected")
    )
