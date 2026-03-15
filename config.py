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

    # Jira REST API (for script: fetch issue + add comment)
    jira_base_url: str = ""  # e.g. https://sanjayrane.atlassian.net
    jira_email: str = ""    # Atlassian account email
    jira_api_token: str = ""  # Create at https://id.atlassian.com/manage-profile/security/api-tokens

    # OpenAI (or compatible) LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_api_base: str | None = None  # e.g. Azure OpenAI endpoint


def get_settings() -> Settings:
    return Settings()
