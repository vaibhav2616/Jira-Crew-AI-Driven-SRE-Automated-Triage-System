"""Generic and fallback alert adapter."""

from typing import Any

from src.adapters.base import BaseAlertAdapter
from src.schemas.universal_alert import UniversalAlertPayload


class GenericAlertAdapter(BaseAlertAdapter):
    """
    Normalizes any generic JSON alert from custom microservices,
    payment gateways, or legacy IncomingAlert formats into UniversalAlertPayload.
    """

    def adapt(self, raw_payload: dict[str, Any]) -> UniversalAlertPayload:
        # Determine service name
        service = (
            raw_payload.get("service_name")
            or raw_payload.get("service")
            or raw_payload.get("app")
            or raw_payload.get("application")
            or "unknown-service"
        )

        # Determine error message
        error_msg = (
            raw_payload.get("error_message")
            or raw_payload.get("error")
            or raw_payload.get("message")
            or raw_payload.get("detail")
            or "System error reported"
        )

        # Determine error type
        error_type = (
            raw_payload.get("error_type")
            or raw_payload.get("exception_type")
            or raw_payload.get("exception")
            or raw_payload.get("type")
        )

        # Logs and metrics
        raw_logs = (
            raw_payload.get("raw_logs")
            or raw_payload.get("logs")
            or raw_payload.get("stacktrace")
            or {}
        )
        metrics = raw_payload.get("metrics") or {}
        trace_id = raw_payload.get("trace_id") or raw_payload.get("x-trace-id")
        tags = raw_payload.get("tags") or {}

        environment = (
            raw_payload.get("environment") or raw_payload.get("env") or "production"
        )

        return UniversalAlertPayload(
            service_name=str(service),
            environment=str(environment),
            error_message=str(error_msg),
            error_type=str(error_type) if error_type else None,
            raw_logs=raw_logs
            if isinstance(raw_logs, (dict, list))
            else {"log": str(raw_logs)},
            metrics=metrics if isinstance(metrics, dict) else {"metric_raw": metrics},
            trace_id=str(trace_id) if trace_id else None,
            tags={str(k): str(v) for k, v in tags.items()}
            if isinstance(tags, dict)
            else {},
        )
