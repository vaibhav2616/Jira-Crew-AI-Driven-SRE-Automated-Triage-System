"""Unit tests for SRE Triage Client SDK."""

import os
import sys

import httpx
import pytest

# Add SDK path to sys.path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk", "python"))
)

from sre_triage_sdk import SRETriageClient, triage_on_failure


def test_sdk_report_incident_success() -> None:
    """Verify SRETriageClient.report_incident posts JSON and parses response."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=201,
            json={
                "status": "ticket_created",
                "issue_key": "KAN-101",
                "summary": "[High] Triage: payment-gateway - Timeout",
            },
        )

    client = SRETriageClient(endpoint="http://mock-triage:8000/api/v1/triage/ingest")
    transport = httpx.MockTransport(mock_handler)
    real_client = httpx.Client
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "sre_triage_sdk.client.httpx.Client",
            lambda **kwargs: real_client(transport=transport, **kwargs),
        )
        res = client.report_incident(
            service_name="payment-gateway",
            error_message="Database pool connection timed out",
            error_type="ConnectionTimeout",
            raw_logs={"active_conns": 100},
        )
        assert res["status"] == "ticket_created"
        assert res["issue_key"] == "KAN-101"


@pytest.mark.asyncio
async def test_sdk_async_report_incident_success() -> None:
    """Verify SRETriageClient.async_report_incident async request."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=201,
            json={"status": "deduplicated", "issue_key": "KAN-101"},
        )

    client = SRETriageClient(endpoint="http://mock-triage:8000/api/v1/triage/ingest")
    transport = httpx.MockTransport(mock_handler)
    real_async = httpx.AsyncClient
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "sre_triage_sdk.client.httpx.AsyncClient",
            lambda **kwargs: real_async(transport=transport, **kwargs),
        )
        res = await client.async_report_incident(
            service_name="payment-gateway",
            error_message="Database pool connection timed out",
        )
        assert res["status"] == "deduplicated"
        assert res["issue_key"] == "KAN-101"


def test_sdk_fail_silent_false_raises() -> None:
    """Verify fail_silent=False raises on network error."""

    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = SRETriageClient(
        endpoint="http://mock-triage:8000/api/v1/triage/ingest", fail_silent=False
    )
    transport = httpx.MockTransport(fail_handler)
    real_client = httpx.Client
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "sre_triage_sdk.client.httpx.Client",
            lambda **kwargs: real_client(transport=transport, **kwargs),
        )
        with pytest.raises(httpx.ConnectError):
            client.report_incident(
                service_name="payment-gateway", error_message="Fatal fail"
            )


@pytest.mark.asyncio
async def test_sdk_async_fail_silent_false_raises() -> None:
    """Verify async fail_silent=False raises on network error."""

    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = SRETriageClient(
        endpoint="http://mock-triage:8000/api/v1/triage/ingest", fail_silent=False
    )
    transport = httpx.MockTransport(fail_handler)
    real_async = httpx.AsyncClient
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "sre_triage_sdk.client.httpx.AsyncClient",
            lambda **kwargs: real_async(transport=transport, **kwargs),
        )
        with pytest.raises(httpx.ConnectError):
            await client.async_report_incident(
                service_name="payment-gateway", error_message="Fatal fail"
            )


def test_sdk_capture_exception_and_decorator_sync() -> None:
    """Verify @triage_on_failure decorator on synchronous functions."""
    dispatched = []

    def mock_report(
        service_name: str, error_message: str, **kwargs: object
    ) -> dict[str, str]:
        dispatched.append((service_name, error_message))
        return {"status": "ok"}

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            SRETriageClient,
            "report_incident",
            lambda self, **kwargs: mock_report(**kwargs),
        )

        @triage_on_failure(service_name="payment-service")
        def pay(amount: int) -> int:
            if amount < 0:
                raise ValueError("Negative amount rejected")
            return amount

        # Successful run does not trigger triage
        assert pay(100) == 100
        assert len(dispatched) == 0

        # Failing run triggers triage before re-raising
        with pytest.raises(ValueError) as exc_info:
            pay(-50)
        assert "Negative amount" in str(exc_info.value)
        assert len(dispatched) == 1
        assert dispatched[0][0] == "payment-service"
        assert "Negative amount rejected" in dispatched[0][1]


@pytest.mark.asyncio
async def test_sdk_decorator_async() -> None:
    """Verify @triage_on_failure decorator on async functions."""
    dispatched = []

    async def mock_async_report(
        service_name: str, error_message: str, **kwargs: object
    ) -> dict[str, str]:
        dispatched.append((service_name, error_message))
        return {"status": "ok"}

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            SRETriageClient,
            "async_report_incident",
            lambda self, **kwargs: mock_async_report(**kwargs),
        )

        @triage_on_failure(service_name="payment-async")
        async def async_pay(success: bool) -> str:
            if not success:
                raise ConnectionError("Gateway 504")
            return "paid"

        res = await async_pay(True)
        assert res == "paid"
        assert len(dispatched) == 0

        with pytest.raises(ConnectionError):
            await async_pay(False)
        assert len(dispatched) == 1
        assert dispatched[0][0] == "payment-async"
