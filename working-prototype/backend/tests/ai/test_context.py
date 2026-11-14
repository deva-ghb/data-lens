from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import context as ai_context
from app.ai.context import answer_question, build_context
from app.ai.decisions import Decisions
from app.engine.run import run_scores
from app.models import AuditEntry, Permit, Person, Shift
from app.models.roster import ShiftKind
from app.models.scores import RunKind


def _person(session: Session, email: str) -> Person:
    return session.scalars(select(Person).where(Person.email == email)).one()


def _scored(session: Session) -> None:
    shift = session.scalars(
        select(Shift).where(Shift.date == date(2026, 7, 29), Shift.kind == ShiftKind.NIGHT)
    ).one()
    run_scores(session, shift.id, RunKind.EVENING)


def _text(value: object) -> str:
    return str(value).lower()


def test_planner_context_has_no_health_detail(scenario: Session) -> None:
    _scored(scenario)
    planner = _person(scenario, "daniel.mensah@mirsalterminals.com")
    context = build_context(scenario, planner, "brief")
    assert "site_tiers" in context
    assert "health_detail" not in context
    blob = _text(context)
    for word in ("creatinine", "hba1c", "sodium", "lab panel", "syndrome"):
        assert word not in blob


def test_permit_context_has_counts_not_names(scenario: Session) -> None:
    _scored(scenario)
    issuer = _person(scenario, "priya.raman@mirsalterminals.com")
    permit = scenario.scalars(select(Permit).where(Permit.number.like("PTW-260729-N-%"))).first()
    assert permit is not None
    context = build_context(scenario, issuer, "permit", permit.id)
    counts = context["permit_counts"]["readiness"]
    assert set(counts) >= {"fit", "fit_with_controls", "reassign", "refer", "unknown"}
    blob = _text(context)
    assert "arjun" not in blob and "thapa" not in blob


def test_planner_question_about_lab_results_is_declined_and_audited(
    scenario: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    planner = _person(scenario, "daniel.mensah@mirsalterminals.com")
    calls = {"text": 0}

    def fake_decide(session, subject_kind, subject_id, input_value, questions):  # type: ignore[no-untyped-def]
        answers = {
            "data_needed": {"type": "choice", "name": "data_needed", "choice": "health_detail"},
            "needs_health_detail": {
                "type": "predicate",
                "name": "needs_health_detail",
                "probability": 0.97,
            },
        }
        return Decisions(1, answers)

    def fake_draft(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["text"] += 1
        raise AssertionError("no text should be generated for a declined question")

    monkeypatch.setattr(ai_context, "decide", fake_decide)
    monkeypatch.setattr(ai_context, "get_or_draft", fake_draft)
    before = scenario.scalar(
        select(func.count()).select_from(AuditEntry).where(AuditEntry.action == "question_declined")
    )
    reply = answer_question(scenario, planner, "Which workers had high creatinine this month?")
    assert reply.declined is True
    assert "health" in reply.text.lower()
    assert calls["text"] == 0
    after = scenario.scalar(
        select(func.count()).select_from(AuditEntry).where(AuditEntry.action == "question_declined")
    )
    assert after == (before or 0) + 1
