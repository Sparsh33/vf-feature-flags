"""Application settings loaded from environment / .env via pydantic-settings."""

from typing import List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that must never be accepted as JWT_SECRET outside of local dev — these
# have shipped in example configs, docs, or compose defaults and are therefore
# publicly known. Keeping the set in one place makes it easy to extend.
INSECURE_JWT_SECRETS = frozenset(
    {
        "change-me-in-prod",
        "dev-insecure-change-me",
        "",
    }
)
LOCAL_ENV = "local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = Field(default=LOCAL_ENV)
    mongo_uri: str = Field(default="mongodb://mongo:27017")
    mongo_db: str = Field(default="vf_feature_flags")
    redis_url: str = Field(default="redis://redis:6379/0")
    celery_broker_url: str = Field(default="redis://redis:6379/1")
    jwt_secret: str = Field(default="change-me-in-prod")
    jwt_ttl_minutes: int = Field(default=1440)
    anthropic_api_key: str = Field(default="")
    nl_provider: str = Field(default="ollama")
    ollama_base_url: str = Field(default="http://host.docker.internal:11434")
    ollama_model: str = Field(default="llama3.1:8b")
    nl_input_token_budget: int = Field(default=8192)
    nl_compaction_trigger: float = Field(default=0.70)
    cors_origins: str = Field(default="http://localhost:5173")

    @model_validator(mode="after")
    def _reject_insecure_jwt_secret_outside_local(self) -> "Settings":
        if self.env == LOCAL_ENV:
            return self
        if self.jwt_secret in INSECURE_JWT_SECRETS:
            raise ValueError(
                f"JWT_SECRET must be set to a non-default, non-empty value when ENV='{self.env}' "
                "(detected a well-known insecure default). Generate a random secret "
                "(e.g. `openssl rand -hex 32`) and set JWT_SECRET in your environment."
            )
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
