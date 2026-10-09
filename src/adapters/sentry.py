"""Adapter for Sentry incident webhook payloads."""

from typing import Any

from src.adapters.base import BaseAlertAdapter
from src.schemas.universal_alert import UniversalAlertPayload


class SentryAdapter(BaseAlertAdapter):
    """
    Normalizes Sentry webhook payloads into UniversalAlertPayload.
    Extracts issue titles, tags, culprit functions, and trace contexts.
    """

    def adapt(self, raw_payload: dict[str, Any]) -> UniversalAlertPayload:
        data = raw_payload.get("data", raw_payload)
        event = data.get("event", data)

        project = (
            raw_payload.get("project_slug")
            or event.get("project")
            or data.get("project_name")
            or "sentry-app"
        )

        title = (
            event.get("title")
            or event.get("message")
            or data.get("message")
            or "Unhandled exception in application"
        )

        culprit = event.get("culprit", "")
        tags_raw = event.get("tags", [])
        tags_dict: dict[str, str] = {}
        if isinstance(tags_raw, list):
            for item in tags_raw:
                if isinstance(item, list) and len(item) == 2:
                    tags_dict[str(item[0])] = str(item[1])
                elif isinstance(item, dict) and "key" in item and "value" in item:
                    tags_dict[str(item["key"])] = str(item["value"])
        elif isinstance(tags_raw, dict):
            tags_dict = {str(k): str(v) for k, v in tags_raw.items()}

        contexts = event.get("contexts", {})
        trace_context = contexts.get("trace", {})
        trace_id = trace_context.get("trace_id") or tags_dict.get("trace_id")

        return UniversalAlertPayload(
            service_name=project,
            environment=event.get(
                "environment", tags_dict.get("environment", "production")
            ),
            error_message=f"{title} ({culprit})" if culprit else title,
            error_type=event.get("type", tags_dict.get("mechanism", "SentryError")),
            raw_logs=event,
            metrics={
                "level": event.get("level", "error"),
                "culprit": culprit,
                "platform": event.get("platform", "unknown"),
            },
            trace_id=trace_id,
            tags=tags_dict,
        )
