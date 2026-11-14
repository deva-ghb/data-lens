import secrets
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# working-prototype/.env, two levels above this file's package directory.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Without DATALENS_JWT_SECRET, a random secret is generated once and kept in
# backend/data/.secret (git-ignored), so no signing key ever lives in the source.
SECRET_FILE = Path(__file__).resolve().parents[1] / "data" / ".secret"


def local_secret() -> str:
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text().strip()
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    value = secrets.token_hex(32)
    SECRET_FILE.write_text(value)
    SECRET_FILE.chmod(0o600)
    return value


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
    jwt_secret: str = Field(default_factory=local_secret, validation_alias="DATALENS_JWT_SECRET")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """The project's own .env wins over variables exported in the user's shell, so a
        key set for another project can never be sent to this one's endpoint."""
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

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
