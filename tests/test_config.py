"""Tests for configuration management."""

import os
from unittest.mock import patch

from src.config import Settings


def test_settings_default_values() -> None:
    """Verify default values when environment variables are omitted."""
    settings = Settings(
        JIRA_DOMAIN="myorg.atlassian.net",
        JIRA_EMAIL="sre@myorg.com",
        JIRA_API_TOKEN="tok123",
        GEMINI_API_KEY="gem123",
    )
    assert settings.JIRA_PROJECT_KEY == "KAN"
    assert settings.jira_base_url == "https://myorg.atlassian.net"


def test_settings_url_normalization() -> None:
    """Verify URL normalization handles trailing slashes and existing protocols."""
    settings1 = Settings(JIRA_DOMAIN="https://corp.atlassian.net/")
    assert settings1.jira_base_url == "https://corp.atlassian.net"

    settings2 = Settings(JIRA_DOMAIN="http://corp.internal:8080/")
    assert settings2.jira_base_url == "http://corp.internal:8080"

    settings3 = Settings(JIRA_DOMAIN="test.atlassian.net")
    assert settings3.jira_base_url == "https://test.atlassian.net"


def test_settings_from_env_vars() -> None:
    """Verify loading from environment variables."""
    env = {
        "JIRA_DOMAIN": "env-corp.atlassian.net",
        "JIRA_EMAIL": "env-user@corp.com",
        "JIRA_API_TOKEN": "env-token-xyz",
        "JIRA_PROJECT_KEY": "SRE",
        "GEMINI_API_KEY": "env-gemini-key",
    }
    with patch.dict(os.environ, env, clear=True):
        settings = Settings()
        assert settings.JIRA_DOMAIN == "env-corp.atlassian.net"
        assert settings.JIRA_EMAIL == "env-user@corp.com"
        assert settings.JIRA_API_TOKEN == "env-token-xyz"
        assert settings.JIRA_PROJECT_KEY == "SRE"
        assert settings.GEMINI_API_KEY == "env-gemini-key"


def test_settings_warns_on_placeholder_secrets() -> None:
    """Verify that default placeholder tokens trigger security warnings."""
    import warnings

    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        settings = Settings(
            JIRA_API_TOKEN="mock-jira-api-token",
            GEMINI_API_KEY="mock-gemini-api-key",
        )
        assert settings.JIRA_API_TOKEN == "mock-jira-api-token"
        assert len(recorded_warnings) >= 2
        messages = [str(w.message) for w in recorded_warnings]
        assert any(
            "JIRA_API_TOKEN is using the local-dev placeholder" in m for m in messages
        )
        assert any(
            "GEMINI_API_KEY is using the local-dev placeholder" in m for m in messages
        )


def test_get_settings_cached() -> None:
    """Verify get_settings returns a singleton cached Settings instance."""
    from src.config import get_settings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
