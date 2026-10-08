"""Extended tests for uncovered branches in RedisClient, LLMClient, and TriageService."""

from typing import Any

import httpx
import pytest

from src.infrastructure.exceptions import JiraAPIError
from src.infrastructure.redis_client import RedisClient
from src.schemas.alert import IncomingAlert
from src.services.triage_service import TriageService
from tests.conftest import MockJiraClient, MockLLMClient, MockRedisClient

# ---------------------------------------------------------------------------
# RedisClient – set_dedup connection failure path (lines 143–161)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_set_dedup_connection_error_is_swallowed() -> None:
    """Verify set_dedup fails-open silently when Redis write raises ConnectionError."""

    class BrokenWriteRedis:
        async def get(self, key: str) -> str | None:
            return None

        async def set(self, key: str, value: str, ex: int = 0) -> None:
            raise ConnectionError("write refused")

    client = RedisClient(client=BrokenWriteRedis())  # type: ignore[arg-type]
    # Must NOT raise; failure is swallowed and logged as a warning
    await client.set_dedup("sig-abc", "KAN-99", ttl_seconds=900)


@pytest.mark.asyncio
async def test_redis_fallback_persists_across_check_and_set() -> None:
    """When primary Redis is unreachable, fallback in-memory cache is initialised once and reused."""
    import redis.asyncio as aioredis

    # Broken pool that fails on every connection attempt
    pool: aioredis.ConnectionPool[Any] = aioredis.ConnectionPool.from_url(
        "redis://127.0.0.1:19999",  # non-existent port
        socket_connect_timeout=0.05,
        socket_timeout=0.05,
    )
    client = RedisClient(pool=pool)

    # First call: primary fails → fakeredis fallback initialised → cache MISS
    result1 = await client.check_and_set_dedup("sig-fallback", ttl_seconds=900)
    assert result1 is None

    # Populate via set_dedup (should also use the fallback)
    await client.set_dedup("sig-fallback", "KAN-42", ttl_seconds=900)

    # Second check: fallback should now return the stored key
    result2 = await client.check_and_set_dedup("sig-fallback", ttl_seconds=900)
    assert result2 == "KAN-42"

    await client.aclose()


# ---------------------------------------------------------------------------
# LLMClient – heuristic fallback path (lines 48–86)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_client_invalid_api_key_uses_heuristic_fallback() -> None:
    """Verify API_KEY_INVALID error triggers heuristic diagnosis fallback.

    The fallback only fires when _external_client=False (no injected mock).
    We patch genai.Client.aio.models.generate_content to simulate a bad key.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.infrastructure.llm_client import LLMClient
    from src.schemas.alert import LLMTriageResult

    # Build a fake genai.Client instance that raise the real API_KEY_INVALID error
    mock_internal_client = MagicMock()
    mock_internal_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception(
            "400 API_KEY_INVALID: API key not valid. Please pass a valid API key."
        )
    )

    # Patch genai.Client constructor so LLMClient's internal instantiation returns our mock
    with patch(
        "src.infrastructure.llm_client.genai.Client", return_value=mock_internal_client
    ):
        llm = LLMClient(
            api_key="bad-key"
        )  # _external_client = False → fallback eligible

    result = await llm.analyze_alert(
        service_name="postgres-svc",
        error_message="Postgres connection pool exhausted",
        raw_logs={"active_connections": 150},
    )

    assert isinstance(result, LLMTriageResult)
    assert result.severity_level == "High"
    assert len(result.remediation_runbook) > 0


@pytest.mark.asyncio
async def test_llm_client_malformed_json_raises_exception() -> None:
    """Verify non-JSON / schema-violating Gemini response raises SRETriageException."""
    from unittest.mock import AsyncMock, MagicMock

    from src.infrastructure.exceptions import SRETriageException
    from src.infrastructure.llm_client import LLMClient

    bad_response = MagicMock()
    bad_response.text = '{"root_cause_analysis": "missing severity and runbook"}'

    mock_genai = MagicMock()
    mock_genai.aio.models.generate_content = AsyncMock(return_value=bad_response)

    llm = LLMClient(api_key="mock-key", client=mock_genai)

    with pytest.raises(SRETriageException) as exc_info:
        await llm.analyze_alert(
            service_name="payment-svc",
            error_message="Stripe webhook rejected",
            raw_logs={},
        )
    assert "validate" in str(exc_info.value).lower() or "LLMTriageResult" in str(
        exc_info.value
    )


# ---------------------------------------------------------------------------
# TriageService – httpx network exception boundary (lines 110–121)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_triage_service_jira_read_timeout_raises_jira_api_error() -> None:
    """Verify httpx.ReadTimeout is caught and re-raised as JiraAPIError (→ 502 at API layer)."""

    class TimeoutJiraClient(MockJiraClient):
        async def create_ticket(
            self,
            summary: str,
            description: str | dict[str, Any] = "",
            issue_type: str = "Task",
        ) -> dict[str, Any]:
            raise httpx.ReadTimeout("Jira did not respond within 15s", request=None)

    triage = TriageService(
        jira_client=TimeoutJiraClient(),
        llm_client=MockLLMClient(),
        redis_client=MockRedisClient(),
    )
    alert = IncomingAlert(
        service_name="billing-svc",
        error_message="Charge failed: upstream timeout",
        raw_logs={},
    )

    with pytest.raises(JiraAPIError) as exc_info:
        await triage.process_alert(alert)

    assert exc_info.value.status_code == 504
    assert "ReadTimeout" in exc_info.value.message


@pytest.mark.asyncio
async def test_triage_service_jira_connect_error_raises_jira_api_error() -> None:
    """Verify httpx.ConnectError is caught and re-raised as JiraAPIError."""

    class ConnectErrorJiraClient(MockJiraClient):
        async def create_ticket(
            self,
            summary: str,
            description: str | dict[str, Any] = "",
            issue_type: str = "Task",
        ) -> dict[str, Any]:
            raise httpx.ConnectError("Could not connect to atlassian.net")

    triage = TriageService(
        jira_client=ConnectErrorJiraClient(),
        llm_client=MockLLMClient(),
        redis_client=MockRedisClient(),
    )
    alert = IncomingAlert(
        service_name="shipping-svc",
        error_message="Carrier API unreachable",
        raw_logs={},
    )

    with pytest.raises(JiraAPIError) as exc_info:
        await triage.process_alert(alert)

    assert exc_info.value.status_code == 504
    assert "ConnectError" in exc_info.value.message


# ---------------------------------------------------------------------------
# JiraClient – additional coverage branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jira_client_default_init_and_context_manager() -> None:
    """Verify JiraClient initialization with default client and async context manager."""
    from src.infrastructure.jira_client import JiraClient

    jira = JiraClient(
        domain="https://corp.atlassian.net",
        email="sre@corp.com",
        api_token="tok",
    )
    assert not jira._external_client
    assert jira.base_url == "https://corp.atlassian.net"
    async with jira as client:
        assert client is jira


@pytest.mark.asyncio
async def test_redis_set_dedup_initializes_fallback_when_unreachable() -> None:
    """Verify set_dedup initializes fallback when called first on unreachable Redis."""
    import redis.asyncio as aioredis

    pool: aioredis.ConnectionPool[Any] = aioredis.ConnectionPool.from_url(
        "redis://127.0.0.1:19999",
        socket_connect_timeout=0.05,
        socket_timeout=0.05,
    )
    client = RedisClient(pool=pool)
    await client.set_dedup("sig-direct", "KAN-123", ttl_seconds=900)
    res = await client.check_and_set_dedup("sig-direct", ttl_seconds=900)
    assert res == "KAN-123"
    await client.aclose()


@pytest.mark.asyncio
async def test_jira_client_custom_object_description_and_error_branches() -> None:
    """Verify description conversion for non-str/non-dict and error handling branches."""
    from src.infrastructure.jira_client import JiraClient

    # Test custom object description
    def mock_handler_success(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=201, json={"key": "KAN-10", "id": "10010"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler_success)
    ) as mock_http:
        jira = JiraClient(
            domain="test.atlassian.net",
            email="sre@test.com",
            api_token="tok",
            client=mock_http,
        )
        res = await jira.create_ticket(
            "Test",
            description=12345,  # type: ignore[arg-type]
        )
        assert res["key"] == "KAN-10"

    # Test network error raising httpx.RequestError
    def mock_handler_net_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Network down")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler_net_error)
    ) as mock_http:
        jira = JiraClient(
            domain="test.atlassian.net",
            email="sre@test.com",
            api_token="tok",
            client=mock_http,
        )
        with pytest.raises(httpx.ConnectError):
            await jira.create_ticket("Test", "Desc")

    # Test error response with errors map
    def mock_handler_errors(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=400, json={"errors": {"summary": "Field required"}}
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler_errors)
    ) as mock_http:
        jira = JiraClient(
            domain="test.atlassian.net",
            email="sre@test.com",
            api_token="tok",
            client=mock_http,
        )
        with pytest.raises(JiraAPIError) as exc_info:
            await jira.create_ticket("Test", "Desc")
        assert "Field required" in exc_info.value.message

    # Test error response with non-JSON text
    def mock_handler_text(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=502, text="Bad Gateway From Proxy")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(mock_handler_text)
    ) as mock_http:
        jira = JiraClient(
            domain="test.atlassian.net",
            email="sre@test.com",
            api_token="tok",
            client=mock_http,
        )
        with pytest.raises(JiraAPIError) as exc_info:
            await jira.create_ticket("Test", "Desc")
        assert "Bad Gateway From Proxy" in exc_info.value.message


# ---------------------------------------------------------------------------
# RedisClient – additional error & context manager branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_client_redis_error_and_context_manager() -> None:
    """Verify RedisError is caught safely in check_and_set and set_dedup, and context manager works."""
    from redis.exceptions import RedisError

    class ErrorRedis:
        async def get(self, key: str) -> str | None:
            raise RedisError("Corrupted data")

        async def set(self, key: str, value: str, ex: int = 0) -> None:
            raise RedisError("Write error")

    client = RedisClient(client=ErrorRedis())  # type: ignore[arg-type]
    res = await client.check_and_set_dedup("sig-error")
    assert res is None
    await client.set_dedup("sig-error", "KAN-1")

    # Context manager test
    async with RedisClient() as rc:
        assert isinstance(rc, RedisClient)


# ---------------------------------------------------------------------------
# LLMClient – Medium & Low severity fallback branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_client_fallback_medium_and_low_severity() -> None:
    """Verify Medium and Low severity branches in heuristic fallback."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.infrastructure.llm_client import LLMClient

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("API_KEY_INVALID: bad key")
    )

    with patch("src.infrastructure.llm_client.genai.Client", return_value=mock_client):
        llm = LLMClient(api_key="bad-key")

    res_med = await llm.analyze_alert(
        "search-svc", "API slow query latency degraded", {}
    )
    assert res_med.severity_level == "Medium"
    assert "search-svc" in res_med.root_cause_analysis

    res_low = await llm.analyze_alert(
        "worker-svc", "Minor cache miss count increased", {}
    )
    assert res_low.severity_level == "Low"
