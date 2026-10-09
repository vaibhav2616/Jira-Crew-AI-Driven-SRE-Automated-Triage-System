"""Adapter for Prometheus Alertmanager webhook payloads."""

from typing import Any

from src.adapters.base import BaseAlertAdapter
from src.schemas.universal_alert import UniversalAlertPayload


class AlertmanagerAdapter(BaseAlertAdapter):
    """
    Normalizes Prometheus Alertmanager webhook payloads into UniversalAlertPayload.
    Handles 'alerts' array format with annotations, labels, and generatorURL.
    """

    def adapt(self, raw_payload: dict[str, Any]) -> UniversalAlertPayload:
        alerts = raw_payload.get("alerts", [])
        primary = alerts[0] if alerts else {}

        labels = primary.get("labels", {})
        annotations = primary.get("annotations", {})

        service = (
            labels.get("service")
            or labels.get("job")
            or labels.get("app")
            or raw_payload.get("groupLabels", {}).get("alertname", "unknown-service")
        )

        error_msg = (
            annotations.get("description")
            or annotations.get("summary")
            or annotations.get("message")
            or labels.get("alertname")
            or "Alertmanager firing notification"
        )

        return UniversalAlertPayload(
            service_name=service,
            environment=labels.get("environment", labels.get("env", "production")),
            error_message=error_msg,
            error_type=labels.get("alertname", "PrometheusAlert"),
            raw_logs=primary,
            metrics={
                "status": raw_payload.get("status", "firing"),
                "generator_url": primary.get("generatorURL", ""),
                "alert_count": len(alerts),
            },
            trace_id=labels.get("trace_id"),
            tags={str(k): str(v) for k, v in labels.items()},
        )
