"""Unit tests for asynchronous LLMClient with Google Gemini SDK."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.exceptions import SRETriageException
from src.infrastructure.llm_client import LLMClient
from src.schemas.alert import LLMTriageResult


@pytest.mark.asyncio
async def test_analyze_alert_success() -> None:
    """Verify analyze_alert configures gemini-2.5-flash with LLMTriageResult schema."""
    mock_response = MagicMock()
    mock_response.text = (
        '{"root_cause_analysis": "OIDC provider token endpoint returned 504 Gateway Timeout due to upstream network partition.", '
        '"severity_level": "High", '
        '"remediation_runbook": ["Check Okta status dashboard", "Switch to secondary auth provider", "Flush auth cache"]}'
    )

    mock_generate = AsyncMock(return_value=mock_response)
    mock_genai_client = MagicMock()
    mock_genai_client.aio.models.generate_content = mock_generate

    llm_client = LLMClient(
        api_key="mock-api-key",
        client=mock_genai_client,
        model_name="gemini-2.5-flash",
    )

    result = await llm_client.analyze_alert(
        service_name="auth-service",
        error_message="OIDC provider timeout after 30s",
        raw_logs={"status_code": 504, "latency_ms": 30000},
    )

    # Verify return type and parsed fields
    assert isinstance(result, LLMTriageResult)
    assert result.severity_level == "High"
    assert "OIDC provider token endpoint" in result.root_cause_analysis
    assert len(result.remediation_runbook) == 3
    assert result.remediation_runbook[0] == "Check Okta status dashboard"

    # Verify generate_content call arguments
    mock_generate.assert_called_once()
    call_kwargs = mock_generate.call_args.kwargs

    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert "auth-service" in call_kwargs["contents"]
    assert "Principal SRE" in call_kwargs["contents"]
    assert "504" in call_kwargs["contents"]

    config = call_kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema == LLMTriageResult
    assert "Principal Site Reliability Engineer" in config.system_instruction


@pytest.mark.asyncio
async def test_analyze_alert_empty_response_raises_exception() -> None:
    """Verify empty response text raises SRETriageException."""
    mock_response = MagicMock()
    mock_response.text = ""

    mock_genai_client = MagicMock()
    mock_genai_client.aio.models.generate_content = AsyncMock(
        return_value=mock_response
    )

    llm_client = LLMClient(api_key="mock-api-key", client=mock_genai_client)

    with pytest.raises(SRETriageException) as exc_info:
        await llm_client.analyze_alert(
            service_name="payment-service",
            error_message="Deadlock detected",
            raw_logs={},
        )
    assert "empty response" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_analyze_alert_api_error_raises_exception() -> None:
    """Verify API exception raises SRETriageException."""
    mock_genai_client = MagicMock()
    mock_genai_client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("Google Gemini 503 Service Unavailable")
    )

    llm_client = LLMClient(api_key="mock-api-key", client=mock_genai_client)

    with pytest.raises(SRETriageException) as exc_info:
        await llm_client.analyze_alert(
            service_name="payment-service",
            error_message="Deadlock detected",
            raw_logs={},
        )
    assert "Gemini API failure" in str(exc_info.value)
