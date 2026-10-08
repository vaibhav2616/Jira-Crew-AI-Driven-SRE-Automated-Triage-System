"""Integration tests for alerts API and health check endpoints."""

from collections.abc import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import (
    get_crew_engine,
    get_jira_client,
    get_llm_client,
    get_redis_client,
)
from src.crew.sre_crew import SREIncidentCrew
from src.main import app
from tests.conftest import MockJiraClient, MockLLMClient, MockRedisClient


@pytest.fixture
def client_with_mocks() -> Generator[
    tuple[TestClient, MockJiraClient, MockLLMClient, MockRedisClient], None, None
]:
    """Provide TestClient with dependency overrides for JiraClient, LLMClient, and RedisClient."""
    mock_jira = MockJiraClient()
    mock_llm = MockLLMClient(severity_level="High")
    mock_redis = MockRedisClient()

    app.dependency_overrides[get_jira_client] = lambda: mock_jira
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_crew_engine] = lambda: None

    client = TestClient(app)
    try:
        yield client, mock_jira, mock_llm, mock_redis
    finally:
        app.dependency_overrides.clear()


def test_health_and_root_endpoints(test_client: TestClient) -> None:
    """Verify health and root endpoints return 200 OK."""
    resp = test_client.get("/healthz")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "ok"

    resp = test_client.get("/livez")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "alive"

    resp = test_client.get("/")
    assert resp.status_code == status.HTTP_200_OK
    assert "service" in resp.json()


def test_app_lifespan() -> None:
    """Verify application lifespan startup and shutdown hooks execute cleanly."""
    with TestClient(app) as client:
        resp = client.get("/healthz")
        assert resp.status_code == status.HTTP_200_OK


def test_post_alerts_success_and_deduplication(
    client_with_mocks: tuple[
        TestClient, MockJiraClient, MockLLMClient, MockRedisClient
    ],
) -> None:
    """Verify first alert creates ticket and second identical alert is deduplicated."""
    client, mock_jira, mock_llm, _mock_redis = client_with_mocks

    payload = {
        "service_name": "checkout-api",
        "error_message": "Stripe API 500 internal server error",
        "raw_logs": {
            "request_id": "req-9874",
            "region": "us-east-1",
        },
    }

    # 1. First alert -> creates Jira ticket
    response1 = client.post("/api/v1/alerts", json=payload)

    assert response1.status_code == status.HTTP_201_CREATED
    data1 = response1.json()
    assert data1["status"] == "ticket_created"
    assert data1["issue_key"] == "KAN-1"
    assert (
        data1["summary"]
        == "[High] Triage: checkout-api - Stripe API 500 internal server error"
    )
    assert data1["triage_result"] is not None
    assert len(mock_jira.created_tickets) == 1
    assert len(mock_llm.analyzed_alerts) == 1

    # 2. Second alert (storm simulation) -> deduplicated, zero extra LLM/Jira calls
    response2 = client.post("/api/v1/alerts", json=payload)

    assert response2.status_code == status.HTTP_201_CREATED
    data2 = response2.json()
    assert data2["status"] == "deduplicated"
    assert data2["issue_key"] == "KAN-1"
    assert "[DEDUPLICATED]" in data2["summary"]
    assert data2["triage_result"] is None

    # LLM and Jira invocation counts must NOT increase
    assert len(mock_jira.created_tickets) == 1
    assert len(mock_llm.analyzed_alerts) == 1


def test_post_alerts_validation_error(test_client: TestClient) -> None:
    """Verify missing required fields triggers 422 Unprocessable Content."""
    invalid_payload = {
        "service_name": "checkout-api",
    }
    response = test_client.post("/api/v1/alerts", json=invalid_payload)
    assert response.status_code == 422


def test_post_alerts_jira_error_returns_502() -> None:
    """Verify upstream Jira errors are caught and surfaced as 502 Bad Gateway."""
    failing_jira = MockJiraClient(should_fail=True, fail_status=401)
    mock_llm = MockLLMClient()
    mock_redis = MockRedisClient()

    app.dependency_overrides[get_jira_client] = lambda: failing_jira
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_crew_engine] = lambda: None
    client = TestClient(app)

    try:
        payload = {
            "service_name": "inventory-db",
            "error_message": "Deadlock detected on stock_items table",
            "raw_logs": {},
        }
        response = client.post("/api/v1/alerts", json=payload)
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert "detail" in data
        assert data["detail"]["message"] == "Failed to create Jira triage ticket"
        assert data["detail"]["jira_status_code"] == 401
    finally:
        app.dependency_overrides.clear()


def test_post_alerts_llm_failure_returns_500() -> None:
    """Verify LLM failure during triage returns 500 Internal Server Error."""
    mock_jira = MockJiraClient()
    failing_llm = MockLLMClient(should_fail=True)
    mock_redis = MockRedisClient()

    app.dependency_overrides[get_jira_client] = lambda: mock_jira
    app.dependency_overrides[get_llm_client] = lambda: failing_llm
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_crew_engine] = lambda: None
    client = TestClient(app)

    try:
        payload = {
            "service_name": "payment-api",
            "error_message": "Connection refused",
            "raw_logs": {},
        }
        response = client.post("/api/v1/alerts", json=payload)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        app.dependency_overrides.clear()


def test_post_universal_ingest_payment_gateway_and_deduplication(
    client_with_mocks: tuple[
        TestClient, MockJiraClient, MockLLMClient, MockRedisClient
    ],
) -> None:
    """Verify universal endpoint handles payment gateway payload and deduplicates on repeat."""
    client, mock_jira, _mock_llm, _mock_redis = client_with_mocks

    payload = {
        "service": "payment-gateway",
        "error": "Postgres connection pool exhausted after 15000ms",
        "error_type": "PoolExhaustionError",
        "env": "production",
        "logs": {"active_connections": 100, "max_pool": 100},
        "metrics": {"p99_latency_ms": 4800},
        "trace_id": "trace-pmt-992",
    }

    # 1. First alert -> creates Jira ticket
    response1 = client.post("/api/v1/triage/ingest", json=payload)
    assert response1.status_code == status.HTTP_201_CREATED
    data1 = response1.json()
    assert data1["status"] == "ticket_created"
    assert data1["issue_key"] == "KAN-1"
    assert "payment-gateway" in data1["summary"]
    assert len(mock_jira.created_tickets) == 1

    # 2. Second alert (storm) -> deduplicated
    response2 = client.post("/api/v1/triage/ingest", json=payload)
    assert response2.status_code == status.HTTP_201_CREATED
    data2 = response2.json()
    assert data2["status"] == "deduplicated"
    assert data2["issue_key"] == "KAN-1"
    assert len(mock_jira.created_tickets) == 1  # No new tickets created


def test_post_universal_ingest_alertmanager_format(
    client_with_mocks: tuple[
        TestClient, MockJiraClient, MockLLMClient, MockRedisClient
    ],
) -> None:
    """Verify universal endpoint adapts Prometheus Alertmanager webhooks."""
    client, _mock_jira, _, _ = client_with_mocks

    alertmanager_payload = {
        "status": "firing",
        "alerts": [
            {
                "labels": {
                    "alertname": "DatabaseDeadlockDetected",
                    "service": "billing-service",
                    "environment": "production",
                },
                "annotations": {
                    "description": "Deadlock detected during subscription renewal lock acquisition",
                },
            }
        ],
    }

    response = client.post("/api/v1/triage/ingest", json=alertmanager_payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "ticket_created"
    assert "billing-service" in data["summary"]


def test_post_universal_ingest_jira_error_returns_502() -> None:
    """Verify upstream Jira errors in universal endpoint surface as 502 Bad Gateway."""
    failing_jira = MockJiraClient(should_fail=True, fail_status=503)
    mock_llm = MockLLMClient()
    mock_redis = MockRedisClient()

    app.dependency_overrides[get_jira_client] = lambda: failing_jira
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_crew_engine] = lambda: None
    client = TestClient(app)

    try:
        payload = {
            "service": "payment-api",
            "error": "Deadlock occurred",
        }
        response = client.post("/api/v1/triage/ingest", json=payload)
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert data["detail"]["message"] == "Failed to create Jira triage ticket"
    finally:
        app.dependency_overrides.clear()


def test_post_universal_ingest_with_sre_crew_engine() -> None:
    """Verify universal endpoint executes with live SREIncidentCrew engine fallback."""
    mock_jira = MockJiraClient()
    mock_redis = MockRedisClient()
    crew_engine = SREIncidentCrew()

    app.dependency_overrides[get_jira_client] = lambda: mock_jira
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_crew_engine] = lambda: crew_engine
    client = TestClient(app)

    try:
        payload = {
            "service_name": "payment-gateway",
            "error_message": "Postgres connection pool exhausted after 15000ms",
            "raw_logs": {"active_conns": 100},
        }
        response = client.post("/api/v1/triage/ingest", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "ticket_created"
        assert "[High]" in data["summary"]
        assert "payment-gateway" in data["summary"]
        assert len(mock_jira.created_tickets) == 1
    finally:
        app.dependency_overrides.clear()
