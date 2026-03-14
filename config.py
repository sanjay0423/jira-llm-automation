"""Configuration from environment for Jira LLM triage service."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Auth: Jira Automation sends this in Authorization: Bearer <token>
    jira_triage_token: str = ""

    # OpenAI (or compatible) LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_api_base: str | None = None  # e.g. Azure OpenAI endpoint


def get_settings() -> Settings:
    return Settings()
