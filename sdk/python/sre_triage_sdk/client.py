"""Lightweight client and decorator for forwarding incidents to the SRE Triage System."""

import inspect
import logging
import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any

import httpx

logger = logging.getLogger("sre_triage_sdk")


class SRETriageClient:
    """
    Lightweight client for dispatching incident telemetry to the
    Jira-CrewAI SRE Automated Triage microservice.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:8000/api/v1/triage/ingest",
        timeout: float = 10.0,
        fail_silent: bool = True,
    ) -> None:
        """
        Initialize the SRE Triage client.

        Args:
            endpoint: URL of the SRE triage universal ingestion endpoint
            timeout: Request timeout in seconds
            fail_silent: If True, network failures to the triage service do not raise
        """
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.fail_silent = fail_silent

    def report_incident(
        self,
        service_name: str,
        error_message: str,
        error_type: str | None = None,
        raw_logs: dict[str, Any] | list[Any] | None = None,
        metrics: dict[str, Any] | None = None,
        trace_id: str | None = None,
        tags: dict[str, str] | None = None,
        environment: str = "production",
    ) -> dict[str, Any]:
        """
        Synchronously dispatch an incident payload to the triage microservice.
        """
        payload = {
            "service_name": service_name,
            "environment": environment,
            "error_message": error_message,
            "error_type": error_type,
            "raw_logs": raw_logs or {},
            "metrics": metrics or {},
            "trace_id": trace_id,
            "tags": tags or {},
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.endpoint, json=payload)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                return data
        except Exception as exc:
            logger.warning(
                "Failed to dispatch incident to SRE Triage (%s): %s", self.endpoint, exc
            )
            if not self.fail_silent:
                raise
            return {"status": "dispatch_failed", "error": str(exc)}

    async def async_report_incident(
        self,
        service_name: str,
        error_message: str,
        error_type: str | None = None,
        raw_logs: dict[str, Any] | list[Any] | None = None,
        metrics: dict[str, Any] | None = None,
        trace_id: str | None = None,
        tags: dict[str, str] | None = None,
        environment: str = "production",
    ) -> dict[str, Any]:
        """
        Asynchronously dispatch an incident payload to the triage microservice.
        """
        payload = {
            "service_name": service_name,
            "environment": environment,
            "error_message": error_message,
            "error_type": error_type,
            "raw_logs": raw_logs or {},
            "metrics": metrics or {},
            "trace_id": trace_id,
            "tags": tags or {},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.endpoint, json=payload)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                return data
        except Exception as exc:
            logger.warning(
                "Failed to async dispatch incident to SRE Triage (%s): %s",
                self.endpoint,
                exc,
            )
            if not self.fail_silent:
                raise
            return {"status": "dispatch_failed", "error": str(exc)}

    def capture_exception(
        self,
        service_name: str,
        exception: BaseException,
        raw_logs: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        trace_id: str | None = None,
        tags: dict[str, str] | None = None,
        environment: str = "production",
    ) -> dict[str, Any]:
        """
        Extract exception type and stack trace and report incident.
        """
        tb_str = traceback.format_exc()
        logs = raw_logs or {}
        if isinstance(logs, dict):
            logs["stacktrace"] = tb_str

        return self.report_incident(
            service_name=service_name,
            error_message=str(exception) or type(exception).__name__,
            error_type=type(exception).__name__,
            raw_logs=logs,
            metrics=metrics,
            trace_id=trace_id,
            tags=tags,
            environment=environment,
        )


def triage_on_failure(
    service_name: str,
    endpoint: str = "http://localhost:8000/api/v1/triage/ingest",
    fail_silent: bool = True,
) -> Callable[..., Any]:
    """
    Decorator for critical microservice functions (e.g. payment processing, order checkout).
    Automatically captures unhandled exceptions and triggers SRE triage before re-raising.

    Usage:
        @triage_on_failure(service_name="payment-gateway")
        def process_payment(order_id: str, amount: float):
            ...
    """
    client = SRETriageClient(endpoint=endpoint, fail_silent=fail_silent)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    await client.async_report_incident(
                        service_name=service_name,
                        error_message=str(exc) or type(exc).__name__,
                        error_type=type(exc).__name__,
                        raw_logs={
                            "function": func.__name__,
                            "args_summary": str(args)[:200],
                        },
                    )
                    raise

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    client.capture_exception(
                        service_name=service_name,
                        exception=exc,
                        raw_logs={
                            "function": func.__name__,
                            "args_summary": str(args)[:200],
                        },
                    )
                    raise

            return sync_wrapper

    return decorator
