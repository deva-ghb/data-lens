import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.drafts import get_or_draft
from app.detector.detect import evaluate_zone
from app.models import AiDraft, WarningRecord, Zone
from app.models.warnings import WarningStatus


class Counter:
    calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        Counter.calls += 1
        return httpx.Response(500)


def test_seeded_subjects_never_call_azure(scenario: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        ai_client.settings,
        "azure_openai_endpoint",
        "https://x.services.ai.azure.com/openai/v1/chat/completions",
    )
    monkeypatch.setattr(ai_client.settings, "azure_openai_api_key", "k")
    counter = Counter()
    ai_client.set_transport(httpx.MockTransport(counter))
    try:
        seeded = scenario.scalars(select(AiDraft)).all()
        assert len(seeded) > 50
        assert {d.model for d in seeded} == {"authored-seed"}
        for draft in seeded:
            again = get_or_draft(
                scenario, draft.kind, draft.subject_kind, draft.subject_id, {}, draft.language
            )
            assert again.id is not None
        assert Counter.calls == 0
    finally:
        ai_client.set_transport(None)


def test_authored_figures_match_computed(scenario: Session) -> None:
    camp_c = scenario.scalars(select(Zone).where(Zone.name == "Camp Block C")).one()
    record = scenario.scalars(
        select(WarningRecord).where(
            WarningRecord.zone_id == camp_c.id, WarningRecord.status == WarningStatus.OPEN
        )
    ).one()
    step_1 = scenario.scalars(
        select(AiDraft).where(AiDraft.kind == "warning_step_1", AiDraft.subject_id == record.id)
    ).one()
    evaluation = evaluate_zone(scenario, camp_c.id, record.opened_at.date())
    for c in evaluation.contributions:
        assert f"{c.ratio:.1f}" in step_1.content or f"{c.ratio:.2f}" in step_1.content, c.metric
    assert str(int(evaluation.contributions[0].observed)) in step_1.content
