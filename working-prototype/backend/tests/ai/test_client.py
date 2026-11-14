import json
import logging
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.decisions import Choice, Predicate, Score, decide
from app.ai.drafts import get_or_draft
from app.models import AiDecision, AiDraft

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_KEY = "secret-key-value-123"

DRAFT_OUTPUT = {
    "content": "Camp Block C heat visits are double the usual this week.",
    "sure": ["Heat visits from Camp Block C rose from 2 to 4 a day."],
    "unsure": ["Whether the cooling repair lands before Thursday."],
    "would_change": ["Cooling units back in service."],
    "confidence": 0.8,
    "reasoning": {
        "evidence": ["Clinic visits by syndrome"],
        "rules": ["Two signal classes agree"],
        "inferences": ["Poor sleep in hot rooms"],
        "rejected": ["A stomach bug: no gastro rise"],
    },
}


class Recorder:
    def __init__(self, handler: Any) -> None:
        self.calls = 0
        self.handler = handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return self.handler(request)


def _responses_ok(_: httpx.Request) -> httpx.Response:
    body = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(DRAFT_OUTPUT)}],
            }
        ]
    }
    return httpx.Response(200, json=body)


def _use(monkeypatch: pytest.MonkeyPatch, handler: Any) -> Recorder:
    recorder = Recorder(handler)
    monkeypatch.setattr(
        ai_client.settings,
        "azure_openai_endpoint",
        "https://example.services.ai.azure.com/openai/v1/chat/completions",
    )
    monkeypatch.setattr(ai_client.settings, "azure_openai_api_key", FAKE_KEY)
    ai_client.set_transport(httpx.MockTransport(recorder))
    return recorder


@pytest.fixture(autouse=True)
def _reset_transport():  # type: ignore[no-untyped-def]
    yield
    ai_client.set_transport(None)


def test_stored_draft_reused_without_calling_azure(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = _use(monkeypatch, _responses_ok)
    first = get_or_draft(session, "brief", "person", 7, {"role": "hse_head"})
    assert first.status == "draft" and first.id is not None
    second = get_or_draft(session, "brief", "person", 7, {"role": "hse_head"})
    assert second.id == first.id
    assert recorder.calls == 1


def test_timeout_returns_unavailable_and_stores_nothing(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    _use(monkeypatch, boom)
    draft = get_or_draft(session, "brief", "person", 7, {})
    assert draft.status == "unavailable"
    assert session.scalar(select(func.count()).select_from(AiDraft)) == 0


def test_malformed_json_returns_unavailable(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def junk(_: httpx.Request) -> httpx.Response:
        body = {
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "not json"}]}
            ]
        }
        return httpx.Response(200, json=body)

    _use(monkeypatch, junk)
    assert get_or_draft(session, "brief", "person", 8, {}).status == "unavailable"


def test_unconfigured_endpoint_is_unavailable(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai_client.settings, "azure_openai_endpoint", None)
    assert get_or_draft(session, "brief", "person", 9, {}).status == "unavailable"


def test_decide_parses_predicate_choice_and_score_answers(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded = json.loads((FIXTURES / "decisions_response.json").read_text())
    _use(monkeypatch, lambda _: httpx.Response(200, json=recorded))
    result = decide(
        session,
        "near_miss",
        1,
        "A lasher lost footing on the ladder.",
        [
            Predicate("fall_from_height", "Is this a fall from height hazard?"),
            Choice(
                "incident_type",
                "Which type?",
                [("near_miss", "No injury"), ("injury", "Hurt"), ("property", "Damage")],
            ),
            Score(
                "potential_severity",
                "Rate the potential severity.",
                [
                    ("1 Minor", ""),
                    ("2 Moderate", ""),
                    ("3 Serious", ""),
                    ("4 Major", ""),
                    ("5 Fatal", ""),
                ],
            ),
        ],
    )
    assert result is not None
    assert result.probability("fall_from_height") == 1.0
    assert result.choice("incident_type") == "near_miss"
    assert result.level("potential_severity") == pytest.approx(4.18)
    assert session.scalar(select(func.count()).select_from(AiDecision)) == 1


def test_decide_rejects_more_than_400_questions(session: Session) -> None:
    with pytest.raises(ValueError):
        decide(session, "x", 1, "text", [Predicate(f"q{i}", "?") for i in range(401)])


def test_decide_refusal_answer_is_kept_as_refusal(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = {"model": "gpt-6-luna", "answers": [{"type": "refusal", "name": "q1"}]}
    _use(monkeypatch, lambda _: httpx.Response(200, json=body))
    result = decide(session, "x", 1, "text", [Predicate("q1", "?")])
    assert result is not None and result.refused("q1")
    assert result.probability("q1") is None


def test_env_values_never_logged(
    session: Session, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    _use(monkeypatch, lambda r: httpx.Response(500, json={"error": "boom"}))
    get_or_draft(session, "brief", "person", 10, {})
    assert FAKE_KEY not in caplog.text
