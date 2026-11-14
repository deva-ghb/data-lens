import pytest

from app.config import DEFAULT_DEV_JWT_SECRET, Settings

AZURE_ENV_NAMES = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")


@pytest.fixture(autouse=True)
def hermetic_environment(monkeypatch):
    """Ignore the developer's .env and any shell variables these tests read."""
    for name in ("DATABASE_URL", "DATALENS_JWT_SECRET", "AI_TEXT_MODEL", "AI_DECISIONS_MODEL"):
        monkeypatch.delenv(name, raising=False)
    for name in AZURE_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def make_settings(**values) -> Settings:
    return Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]


def test_azure_v1_base_is_derived_from_chat_completions_endpoint():
    settings = make_settings(
        azure_openai_endpoint="https://fake-name.services.ai.azure.com/openai/v1/chat/completions"
    )
    assert settings.azure_v1_base == "https://fake-name.services.ai.azure.com/openai/v1"


def test_azure_v1_base_is_none_without_endpoint():
    assert make_settings().azure_v1_base is None


def test_empty_azure_endpoint_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "")
    settings = make_settings()
    assert settings.azure_openai_endpoint is None
    assert settings.azure_v1_base is None


def test_blank_azure_endpoint_is_treated_as_unset():
    assert make_settings(azure_openai_endpoint="   ").azure_openai_endpoint is None


def test_azure_v1_base_rejects_endpoint_without_openai_path():
    settings = make_settings(azure_openai_endpoint="https://fake-name.services.ai.azure.com/other")
    with pytest.raises(ValueError):
        _ = settings.azure_v1_base


def test_defaults():
    settings = make_settings()
    assert settings.database_url == "sqlite:///data/datalens.db"
    assert settings.azure_openai_endpoint is None
    assert settings.ai_text_model == "gpt-6-luna"
    assert settings.ai_decisions_model == "gpt-6-luna"
    assert settings.jwt_secret == DEFAULT_DEV_JWT_SECRET


def test_jwt_secret_reads_env_and_falls_back_to_dev_default(monkeypatch):
    monkeypatch.setenv("DATALENS_JWT_SECRET", "from-env")
    assert make_settings().jwt_secret == "from-env"
    monkeypatch.delenv("DATALENS_JWT_SECRET")
    assert make_settings().jwt_secret == DEFAULT_DEV_JWT_SECRET
