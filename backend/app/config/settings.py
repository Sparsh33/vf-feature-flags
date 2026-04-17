"""Application settings loaded from environment / .env via pydantic-settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = Field(default="local")
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

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
