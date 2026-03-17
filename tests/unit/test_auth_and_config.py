import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Settings
from main import verify_bearer


def test_verify_bearer_allows_correct_token(monkeypatch):
    monkeypatch.setenv("JIRA_TRIAGE_TOKEN", "secret-token")
    settings = Settings()  # ensure env is picked up
    assert settings.jira_triage_token == "secret-token"

    # Should not raise
    verify_bearer("Bearer secret-token")


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "token secret-token",
        "Bearer wrong-token",
    ],
)
def test_verify_bearer_rejects_missing_or_wrong_token(monkeypatch, header):
    monkeypatch.setenv("JIRA_TRIAGE_TOKEN", "secret-token")
    with pytest.raises(HTTPException) as exc:
        verify_bearer(header)
    assert exc.value.status_code == 403


def test_settings_defaults_and_env(monkeypatch):
    monkeypatch.setenv("JIRA_TRIAGE_TOKEN", "abc123")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

    settings = Settings()

    assert settings.jira_triage_token == "abc123"
    assert settings.openai_api_key == "sk-test"
    # openai_model has a default; this also confirms env override wiring
    assert settings.openai_model == "gpt-4o-mini"

