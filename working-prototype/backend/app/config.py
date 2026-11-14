from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# working-prototype/.env, two levels above this file's package directory.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Fixed secret for local prototype use only. Set DATALENS_JWT_SECRET to override.
DEFAULT_DEV_JWT_SECRET = "datalens-local-dev-secret-change-me"

_OPENAI_MARKER = "/openai/"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = "sqlite:///data/datalens.db"
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    ai_text_model: str = "gpt-6-luna"
    ai_decisions_model: str = "gpt-6-luna"
    jwt_secret: str = Field(default=DEFAULT_DEV_JWT_SECRET, validation_alias="DATALENS_JWT_SECRET")

    @field_validator("azure_openai_endpoint", "azure_openai_api_key", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        """An empty or blank value in .env means "not configured", not an empty string."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def azure_v1_base(self) -> str | None:
        """The endpoint up to and including `/openai/`, followed by `v1`."""
        if self.azure_openai_endpoint is None:
            return None
        head, marker, _ = self.azure_openai_endpoint.partition(_OPENAI_MARKER)
        if not marker:
            raise ValueError("azure_openai_endpoint does not contain /openai/")
        return f"{head}/openai/v1"


settings = Settings()
