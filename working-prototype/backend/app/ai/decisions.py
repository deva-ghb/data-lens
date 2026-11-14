"""Typed answers from the Decisions API: a probability, a pick from a fixed set, or a score.

Used only where the step really is a yes or no, a choice or a rating: incident triage,
the 5 by 5 risk rating, which data a question needs, column mapping for a new feed, and
whether an inspection note confirms a driver. Answers are stored with provenance.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ai.client import AiUnavailable, decisions
from app.audit import audit
from app.config import settings
from app.models import AiDecision, SiteClock

MAX_QUESTIONS = 400


@dataclass(frozen=True)
class Predicate:
    name: str
    instructions: str

    def payload(self) -> dict[str, Any]:
        return {"name": self.name, "type": "predicate", "instructions": self.instructions}


@dataclass(frozen=True)
class Choice:
    name: str
    instructions: str
    choices: list[tuple[str, str]]

    def payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "choice",
            "instructions": self.instructions,
            "choices": [
                {"value": v, "description": d} if d else {"value": v} for v, d in self.choices
            ],
        }


@dataclass(frozen=True)
class Score:
    name: str
    instructions: str
    levels: list[tuple[str, str]]

    def payload(self) -> dict[str, Any]:
        if not 2 <= len(self.levels) <= 10:
            raise ValueError("A score question needs 2 to 10 levels.")
        return {
            "name": self.name,
            "type": "score",
            "instructions": self.instructions,
            "levels": [
                {"label": label, "description": d} if d else {"label": label}
                for label, d in self.levels
            ],
        }


Question = Predicate | Choice | Score


@dataclass
class Decisions:
    record_id: int
    answers: dict[str, dict[str, Any]]

    def refused(self, name: str) -> bool:
        return self.answers.get(name, {}).get("type") == "refusal"

    def probability(self, name: str) -> float | None:
        return self.answers.get(name, {}).get("probability")

    def choice(self, name: str) -> str | None:
        return self.answers.get(name, {}).get("choice")

    def confidence(self, name: str) -> float | None:
        return self.answers.get(name, {}).get("confidence")

    def level(self, name: str) -> float | None:
        """A score on the question's own scale: level 1 for the first label, and so on."""
        score = self.answers.get(name, {}).get("score")
        return None if score is None else round(float(score) + 1, 2)


def decide(
    session: Session,
    subject_kind: str,
    subject_id: int,
    input_value: Any,
    questions: list[Question],
) -> Decisions | None:
    if not 1 <= len(questions) <= MAX_QUESTIONS:
        raise ValueError("The Decisions API takes 1 to 400 questions per request.")
    payload = [q.payload() for q in questions]
    try:
        data = decisions(input_value, payload)
    except AiUnavailable:
        return None
    answers: dict[str, dict[str, Any]] = {
        str(a["name"]): a for a in data.get("answers", []) if isinstance(a, dict) and a.get("name")
    }
    if not answers:
        return None
    clock = session.get(SiteClock, 1)
    record = AiDecision(
        subject_kind=subject_kind,
        subject_id=subject_id,
        model=str(data.get("model", settings.ai_decisions_model)),
        questions_json=payload,
        answers_json=list(answers.values()),
        created_at=clock.now if clock else datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(record)
    session.flush()
    audit(
        session,
        None,
        "ai_decision",
        subject_kind,
        str(subject_id),
        evidence={"decision_id": record.id, "questions": [q.name for q in questions]},
        model_version=record.model,
    )
    return Decisions(record.id, answers)
