"""Pytest fixtures for unit and integration testing."""

from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.infrastructure.jira_client import JiraClient
from src.main import app
from src.schemas.alert import LLMTriageResult


@pytest.fixture
def mock_settings() -> Settings:
    """Fixture providing deterministic test settings."""
    return Settings(
        JIRA_DOMAIN="test-corp.atlassian.net",
        JIRA_EMAIL="tester@test-corp.com",
        JIRA_API_TOKEN="secret-test-token",
        JIRA_PROJECT_KEY="KAN",
        GEMINI_API_KEY="test-gemini-key",
        REDIS_URL="redis://localhost:6379",
    )


@pytest.fixture
def test_client() -> TestClient:
    """Synchronous FastAPI TestClient."""
    return TestClient(app)


class MockJiraClient(JiraClient):
    """Test double for JiraClient to avoid external network calls."""

    def __init__(self, should_fail: bool = False, fail_status: int = 400) -> None:
        super().__init__(
            domain="test-corp.atlassian.net",
            email="tester@test-corp.com",
            api_token="mock-token",
            project_key="KAN",
        )
        self.should_fail = should_fail
        self.fail_status = fail_status
        self.created_tickets: list[dict[str, Any]] = []

    async def create_ticket(
        self,
        summary: str,
        description: Any,
        issue_type: str = "Task",
    ) -> dict[str, Any]:
        if self.should_fail:
            from src.infrastructure.exceptions import JiraAPIError

            raise JiraAPIError(
                status_code=self.fail_status,
                message="Project KAN does not exist or user lacks permission",
                details={"errorMessages": ["Project key invalid"]},
            )

        ticket = {
            "id": "10042",
            "key": f"KAN-{len(self.created_tickets) + 1}",
            "self": "https://test-corp.atlassian.net/rest/api/3/issue/10042",
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
        }
        self.created_tickets.append(ticket)
        return ticket


class MockLLMClient:
    """Test double for LLMClient to simulate Gemini triage without API calls."""

    def __init__(
        self,
        should_fail: bool = False,
        severity_level: Literal["High", "Medium", "Low"] = "High",
        root_cause: str | None = None,
        runbook: list[str] | None = None,
    ) -> None:
        self.should_fail = should_fail
        self.severity_level = severity_level
        self.root_cause = root_cause
        self.runbook = runbook
        self.analyzed_alerts: list[dict[str, Any]] = []

    async def analyze_alert(
        self,
        service_name: str,
        error_message: str,
        raw_logs: dict[str, Any],
    ) -> LLMTriageResult:
        if self.should_fail:
            from src.infrastructure.exceptions import SRETriageException

            raise SRETriageException("Gemini API rate limit exceeded")

        self.analyzed_alerts.append(
            {
                "service_name": service_name,
                "error_message": error_message,
                "raw_logs": raw_logs,
            }
        )

        return LLMTriageResult(
            root_cause_analysis=(
                self.root_cause
                or f"Diagnosed failure in {service_name}: {error_message}"
            ),
            severity_level=self.severity_level,
            remediation_runbook=(
                self.runbook
                or [
                    f"Check health and metrics for {service_name}",
                    f"Inspect cluster pod logs: kubectl logs -l app={service_name}",
                    "Verify database and cache connectivity",
                ]
            ),
        )


class MockRedisClient:
    """Test double for RedisClient to simulate deduplication caching without network."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.cache: dict[str, str] = {}
        self.check_calls: list[str] = []
        self.set_calls: list[tuple[str, str, int]] = []

    async def check_and_set_dedup(
        self,
        signature: str,
        ttl_seconds: int = 900,
    ) -> str | None:
        if self.should_fail:
            return None
        self.check_calls.append(signature)
        return self.cache.get(f"alert:dedup:{signature}")

    async def set_dedup(
        self,
        signature: str,
        ticket_key: str,
        ttl_seconds: int = 900,
    ) -> None:
        if self.should_fail:
            return
        self.set_calls.append((signature, ticket_key, ttl_seconds))
        self.cache[f"alert:dedup:{signature}"] = ticket_key

    async def aclose(self) -> None:
        pass


@pytest.fixture
def mock_jira_client() -> MockJiraClient:
    """Fixture providing a fresh MockJiraClient instance."""
    return MockJiraClient()


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Fixture providing a fresh MockLLMClient instance."""
    return MockLLMClient()


@pytest.fixture
def mock_redis_client() -> MockRedisClient:
    """Fixture providing a fresh MockRedisClient instance."""
    return MockRedisClient()
