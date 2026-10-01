"""Configuration management for the AI-driven SRE Automated Triage System.

Loads and validates settings from environment variables and .env files using Pydantic Settings.
"""

import logging
import warnings
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Sentinel strings used as safe local-dev defaults. The validator below emits a
# loud warning (not a crash) when these are detected so production mis-configs
# are surfaced immediately in logs without breaking the test suite.
_MOCK_JIRA_TOKEN = "mock-jira-api-token"
_MOCK_GEMINI_KEY = "mock-gemini-api-key"


class Settings(BaseSettings):
    """Application settings schema backed by environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Jira Integration
    JIRA_DOMAIN: str = Field(
        default="your-name.atlassian.net",
        description="Atlassian Jira domain (e.g., your-name.atlassian.net)",
    )
    JIRA_EMAIL: str = Field(
        default="sre@example.com",
        description="Atlassian account email address for API authentication",
    )
    JIRA_API_TOKEN: str = Field(
        default=_MOCK_JIRA_TOKEN,
        description="Atlassian API token with issue creation permissions",
    )
    JIRA_PROJECT_KEY: str = Field(
        default="KAN",
        description="Target Jira project key where triage tickets are created",
    )

    # Gemini AI Integration
    GEMINI_API_KEY: str = Field(
        default=_MOCK_GEMINI_KEY,
        description="Google Gemini API key for automated triage reasoning",
    )

    # Multi-Provider Free-Tier LLM Engine (Gemini / Ollama / Groq)
    LLM_PROVIDER: str = Field(
        default="gemini",
        description="Active LLM provider: 'gemini' (Free via AI Studio), 'ollama' (Local Offline), or 'groq' (Free)",
    )
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL for 100% offline local LLM execution",
    )
    OLLAMA_MODEL: str = Field(
        default="llama3.2",
        description="Local Ollama model identifier (e.g., llama3.2, qwen2.5-coder)",
    )
    GROQ_API_KEY: str | None = Field(
        default=None,
        description="Optional Groq API key for ultra-fast free tier Llama inference",
    )
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model identifier",
    )
    CREWAI_PROCESS_TIMEOUT: int = Field(
        default=60,
        description="Maximum execution timeout in seconds for multi-agent SRE crew triage",
    )

    # Redis Deduplication Cache
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for alert deduplication caching",
    )

    # Server Runtime Settings
    HOST: str = Field(
        default="0.0.0.0", description="Host interface to bind the server"
    )
    PORT: int = Field(default=8000, description="Port to bind the server")
    LOG_LEVEL: str = Field(
        default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)"
    )

    @model_validator(mode="after")
    def warn_on_placeholder_secrets(self) -> "Settings":
        """Emit loud warnings when placeholder secrets are detected in the active config."""
        if self.JIRA_API_TOKEN == _MOCK_JIRA_TOKEN:
            warnings.warn(
                "SECURITY: JIRA_API_TOKEN is using the local-dev placeholder value. "
                "Set a real Atlassian API token via the JIRA_API_TOKEN environment variable "
                "or .env file before deploying to production.",
                stacklevel=2,
            )
        if self.GEMINI_API_KEY == _MOCK_GEMINI_KEY:
            warnings.warn(
                "SECURITY: GEMINI_API_KEY is using the local-dev placeholder value. "
                "Set a real Google Gemini API key via the GEMINI_API_KEY environment variable "
                "or .env file before deploying to production.",
                stacklevel=2,
            )
        return self

    @property
    def jira_base_url(self) -> str:
        """Return normalized base URL for Jira API calls with https scheme."""
        domain = self.JIRA_DOMAIN.strip().rstrip("/")
        if not domain.startswith("http://") and not domain.startswith("https://"):
            return f"https://{domain}"
        return domain


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (singleton pattern for DI)."""
    return Settings()
