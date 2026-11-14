import pytest

from app.config import DEFAULT_DEV_JWT_SECRET, Settings


def test_azure_v1_base_is_derived_from_chat_completions_endpoint():
    settings = Settings(
        azure_openai_endpoint="https://fake-name.services.ai.azure.com/openai/v1/chat/completions"
    )
    assert settings.azure_v1_base == "https://fake-name.services.ai.azure.com/openai/v1"


def test_azure_v1_base_is_none_without_endpoint():
    assert Settings(azure_openai_endpoint=None).azure_v1_base is None


def test_azure_v1_base_rejects_endpoint_without_openai_path():
    settings = Settings(azure_openai_endpoint="https://fake-name.services.ai.azure.com/other")
    with pytest.raises(ValueError):
        _ = settings.azure_v1_base


def test_defaults():
    settings = Settings(azure_openai_endpoint=None)
    assert settings.database_url == "sqlite:///data/datalens.db"
    assert settings.ai_text_model == "gpt-6-luna"
    assert settings.ai_decisions_model == "gpt-6-luna"


def test_jwt_secret_reads_env_and_falls_back_to_dev_default(monkeypatch):
    monkeypatch.setenv("DATALENS_JWT_SECRET", "from-env")
    assert Settings().jwt_secret == "from-env"
    monkeypatch.delenv("DATALENS_JWT_SECRET")
    assert Settings().jwt_secret == DEFAULT_DEV_JWT_SECRET
