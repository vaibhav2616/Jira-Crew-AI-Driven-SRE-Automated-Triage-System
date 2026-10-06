"""Unit tests for TriageService with LLM and Redis deduplication integration."""

import pytest

from src.schemas.alert import IncomingAlert
from src.services.triage_service import TriageService
from tests.conftest import MockJiraClient, MockLLMClient, MockRedisClient


def test_incoming_alert_generate_signature() -> None:
    """Verify IncomingAlert.generate_signature produces consistent SHA-256 hash."""
    alert1 = IncomingAlert(
        service_name="payment-service",
        error_message="Connection timed out after 30s",
        raw_logs={"pod": "pod-1", "ts": "2026-10-12T10:00:00Z"},
    )
    alert2 = IncomingAlert(
        service_name="payment-service",
        error_message="Connection timed out after 30s",
        raw_logs={"pod": "pod-2", "ts": "2026-10-12T10:00:05Z"},
    )
    alert_diff_service = IncomingAlert(
        service_name="auth-service",
        error_message="Connection timed out after 30s",
        raw_logs={},
    )

    sig1 = alert1.generate_signature()
    sig2 = alert2.generate_signature()
    sig3 = alert_diff_service.generate_signature()

    assert len(sig1) == 64
    assert (
        sig1 == sig2
    )  # Same service and error_message prefix despite different telemetry
    assert sig1 != sig3  # Different service


@pytest.mark.asyncio
async def test_triage_service_deduplication_halts_pipeline() -> None:
    """Verify alert storm deduplication halts LLM and Jira creation on recurring alert."""
    mock_jira = MockJiraClient()
    mock_llm = MockLLMClient(severity_level="High")
    mock_redis = MockRedisClient()

    triage_service = TriageService(
        jira_client=mock_jira,
        llm_client=mock_llm,
        redis_client=mock_redis,
    )

    alert = IncomingAlert(
        service_name="payment-gateway",
        error_message="Postgres connection pool exhausted: timeout waiting for connection",
        raw_logs={"pod": "pod-1", "active_connections": 100},
    )

    # 1. First alert: Cache MISS -> Runs LLM + Creates Jira ticket -> Stores in Redis
    resp1 = await triage_service.process_alert(alert)

    assert resp1.status == "ticket_created"
    assert resp1.issue_key == "KAN-1"
    assert len(mock_llm.analyzed_alerts) == 1
    assert len(mock_jira.created_tickets) == 1
    assert len(mock_redis.set_calls) == 1
    assert mock_redis.set_calls[0][1] == "KAN-1"
    assert mock_redis.set_calls[0][2] == 900  # 15 minutes TTL

    # 2. Duplicate alert (same error, recurring storm): Cache HIT -> Halts immediately!
    alert_storm = IncomingAlert(
        service_name="payment-gateway",
        error_message="Postgres connection pool exhausted: timeout waiting for connection",
        raw_logs={"pod": "pod-2", "active_connections": 100},  # Different pod telemetry
    )

    resp2 = await triage_service.process_alert(alert_storm)

    # Assertions on deduplication response
    assert resp2.status == "deduplicated"
    assert resp2.issue_key == "KAN-1"
    assert "[DEDUPLICATED]" in resp2.summary
    assert resp2.triage_result is None

    # CRITICAL: Pipeline was halted; neither LLM nor Jira was invoked for the duplicate!
    assert len(mock_llm.analyzed_alerts) == 1
    assert len(mock_jira.created_tickets) == 1


@pytest.mark.asyncio
async def test_triage_service_truncates_long_error_message_to_50_chars() -> None:
    """Verify error_message is sliced to 50 characters in Jira summary."""
    mock_jira = MockJiraClient()
    mock_llm = MockLLMClient(severity_level="Medium")
    mock_redis = MockRedisClient()
    triage_service = TriageService(
        jira_client=mock_jira,
        llm_client=mock_llm,
        redis_client=mock_redis,
    )

    long_error = "This is an extremely long error message that exceeds fifty characters by a wide margin"
    alert = IncomingAlert(
        service_name="auth-service",
        error_message=long_error,
        raw_logs={},
    )

    response = await triage_service.process_alert(alert)

    expected_summary = f"[Medium] Triage: auth-service - {long_error[:50]}"
    assert response.summary == expected_summary
    assert response.status == "ticket_created"


@pytest.mark.asyncio
async def test_triage_service_handles_low_severity() -> None:
    """Verify summary with Low severity level."""
    mock_jira = MockJiraClient()
    mock_llm = MockLLMClient(severity_level="Low")
    mock_redis = MockRedisClient()
    triage_service = TriageService(
        jira_client=mock_jira,
        llm_client=mock_llm,
        redis_client=mock_redis,
    )

    alert = IncomingAlert(
        service_name="metrics-collector",
        error_message="Slow scraper response",
        raw_logs={},
    )

    response = await triage_service.process_alert(alert)
    assert response.summary == "[Low] Triage: metrics-collector - Slow scraper response"
    assert response.status == "ticket_created"
