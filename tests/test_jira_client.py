"""Unit tests for JiraClient and ADF serialization."""

import base64
import json
from typing import Any

import httpx
import pytest

from src.infrastructure.exceptions import JiraAPIError
from src.infrastructure.jira_client import JiraClient


def test_build_adf_description_empty() -> None:
    """Verify empty text generates valid empty ADF doc."""
    doc = JiraClient.build_adf_description("")
    assert doc == {
        "version": 1,
        "type": "doc",
        "content": [],
    }


def test_build_adf_description_content() -> None:
    """Verify text generates proper ADF v1 paragraph and text nodes."""
    sample_text = "Connection timed out after 30000ms"
    doc = JiraClient.build_adf_description(sample_text)

    assert doc["version"] == 1
    assert doc["type"] == "doc"
    assert len(doc["content"]) == 1

    paragraph = doc["content"][0]
    assert paragraph["type"] == "paragraph"
    assert len(paragraph["content"]) == 1

    text_node = paragraph["content"][0]
    assert text_node["type"] == "text"
    assert text_node["text"] == sample_text


def test_build_adf_description_structured_triage() -> None:
    """Verify rich ADF document generated for structured triage result."""
    doc = JiraClient.build_adf_description(
        root_cause_analysis="Connection starvation in database pool.",
        remediation_runbook=["Check pg_stat_activity", "Restart backend service"],
        error_message="504 Gateway Timeout",
        raw_logs={"cluster": "prod-1", "retries": 3},
    )

    assert doc["version"] == 1
    assert doc["type"] == "doc"
    content_types = [node["type"] for node in doc["content"]]

    # Heading, paragraph, heading, orderedList, heading, paragraph, heading, codeBlock
    assert "heading" in content_types
    assert "paragraph" in content_types
    assert "orderedList" in content_types
    assert "codeBlock" in content_types

    # Verify orderedList contents
    ordered_list = next(
        node for node in doc["content"] if node["type"] == "orderedList"
    )
    assert len(ordered_list["content"]) == 2
    first_item = ordered_list["content"][0]
    assert first_item["type"] == "listItem"
    assert first_item["content"][0]["content"][0]["text"] == "Check pg_stat_activity"


def test_build_adf_description_multi_agent_crew_fields() -> None:
    """Verify ADF generation with all multi-agent Crew SRE triage fields."""
    doc = JiraClient.build_adf_description(
        root_cause_analysis="Postgres row lock contention on payment balance debit.",
        remediation_runbook=["Kill blocking PIDs", "Rollout restart"],
        error_message="Transaction deadlock",
        raw_logs={"account_id": "acc_10"},
        impact_assessment="15% payment degradation on Stripe rail",
        anomalies_detected=["Pool 100/100 full", "Lock age > 25s"],
        rollback_guidance="kubectl rollout undo deployment/payment-gateway",
        preventative_measures=["Deploy PgBouncer", "Enable statement timeouts"],
        trace_id="trace-pmt-7711",
    )

    assert doc["version"] == 1
    content_types = [node["type"] for node in doc["content"]]
    assert "heading" in content_types
    assert "paragraph" in content_types
    assert "bulletList" in content_types
    assert "orderedList" in content_types
    assert "codeBlock" in content_types

    # Verify bullet lists for anomalies and preventative measures exist
    bullet_lists = [node for node in doc["content"] if node["type"] == "bulletList"]
    assert len(bullet_lists) == 2


@pytest.mark.asyncio
async def test_create_ticket_success_with_string() -> None:
    """Verify create_ticket sends proper payload, headers, and Basic Auth."""
    captured_request: dict[str, Any] = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["headers"] = dict(request.headers)
        captured_request["body"] = json.loads(request.content.decode("utf-8"))

        return httpx.Response(
            status_code=201,
            json={
                "id": "10001",
                "key": "KAN-1",
                "self": "https://test.atlassian.net/rest/api/3/issue/10001",
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_http_client:
        client = JiraClient(
            domain="test.atlassian.net",
            email="sre@test.com",
            api_token="my-secret-token",
            project_key="KAN",
            client=mock_http_client,
        )

        result = await client.create_ticket(
            summary="[High] Triage: payment-service - Database pool exhausted",
            description="Database pool exhausted",
            issue_type="Task",
        )

        # Assertions on client return value
        assert result["id"] == "10001"
        assert result["key"] == "KAN-1"

        # Assertions on captured HTTP request
        assert captured_request["method"] == "POST"
        assert captured_request["url"] == "https://test.atlassian.net/rest/api/3/issue"

        # Verify Basic Auth header
        auth_header = captured_request["headers"]["authorization"]
        assert auth_header.startswith("Basic ")
        encoded_creds = auth_header.split(" ")[1]
        decoded_creds = base64.b64decode(encoded_creds).decode("utf-8")
        assert decoded_creds == "sre@test.com:my-secret-token"

        # Verify Atlassian REST API v3 JSON schema
        body = captured_request["body"]
        assert "fields" in body
        fields = body["fields"]
        assert fields["project"] == {"key": "KAN"}
        assert (
            fields["summary"]
            == "[High] Triage: payment-service - Database pool exhausted"
        )
        assert fields["issuetype"] == {"name": "Task"}

        # Verify ADF description schema
        description_adf = fields["description"]
        assert description_adf["type"] == "doc"
        assert description_adf["version"] == 1
        assert (
            description_adf["content"][0]["content"][0]["text"]
            == "Database pool exhausted"
        )


@pytest.mark.asyncio
async def test_create_ticket_with_adf_dict() -> None:
    """Verify create_ticket accepts and passes pre-built ADF dictionary directly."""
    captured_request: dict[str, Any] = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_request["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            status_code=201,
            json={
                "id": "10002",
                "key": "KAN-2",
                "self": "https://test.atlassian.net/rest/api/3/issue/10002",
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_http_client:
        client = JiraClient(
            domain="test.atlassian.net",
            email="sre@test.com",
            api_token="my-token",
            project_key="KAN",
            client=mock_http_client,
        )

        prebuilt_adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Root Cause Analysis"}],
                }
            ],
        }

        result = await client.create_ticket(
            summary="[Medium] Triage: cache - Redis latency",
            description=prebuilt_adf,
        )

        assert result["key"] == "KAN-2"
        assert captured_request["body"]["fields"]["description"] == prebuilt_adf


@pytest.mark.asyncio
async def test_create_ticket_failure_raises_jira_api_error() -> None:
    """Verify that non-201 status raises JiraAPIError with parsed details."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=400,
            json={
                "errorMessages": ["Project key 'INVALID' does not exist"],
                "errors": {},
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_http_client:
        client = JiraClient(
            domain="test.atlassian.net",
            email="sre@test.com",
            api_token="token",
            project_key="INVALID",
            client=mock_http_client,
        )

        with pytest.raises(JiraAPIError) as exc_info:
            await client.create_ticket(
                summary="Test summary",
                description="Test description",
            )

        err = exc_info.value
        assert err.status_code == 400
        assert "Project key 'INVALID' does not exist" in err.message
