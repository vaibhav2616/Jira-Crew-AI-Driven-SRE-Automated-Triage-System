"""Universal Alert Schema for SRE Automated Triage.

Designed to ingest incident telemetry from ANY distributed system (e.g., payment gateways,
microservices, serverless functions) and standard observability tools (Prometheus Alertmanager,
Datadog, Grafana, Sentry).
"""

import hashlib
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class UniversalAlertPayload(BaseModel):
    """
    Universal ingestion schema for distributed alerts and incident telemetry.
    Compatible with any microservice, payment gateway, or monitoring platform.
    """

    service_name: str = Field(
        ...,
        description="Name of the impacted service (e.g., payment-gateway, auth-api)",
        examples=["payment-gateway"],
    )
    environment: str = Field(
        default="production",
        description="Execution environment (e.g., production, staging, dev)",
        examples=["production"],
    )
    error_message: str = Field(
        ...,
        description="Primary error message, panic, or alert notification text",
        examples=[
            "Postgres connection pool exhausted: timeout waiting for connection after 15000ms"
        ],
    )
    error_type: str | None = Field(
        default=None,
        description="Machine-readable error class, exception name, or alert rule identifier",
        examples=["ConnectionPoolStarvationError"],
    )
    raw_logs: dict[str, Any] | list[Any] = Field(
        default_factory=dict,
        description="Raw diagnostic log excerpts, stack traces, or request payloads",
        examples=[{"active_connections": 100, "max_pool": 100, "queue_depth": 42}],
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic system metrics at the moment of failure (latencies, resource saturation)",
        examples=[{"p99_latency_ms": 3200, "cpu_usage_pct": 89.4}],
    )
    trace_id: str | None = Field(
        default=None,
        description="Distributed trace ID (e.g., W3C traceparent, OpenTelemetry, Zipkin) for correlation",
        examples=["4bf92f3577b34da6a3ce929d0e0e4736"],
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary contextual tags (cloud provider, region, cluster, payment provider)",
        examples=[
            {
                "region": "us-east-1",
                "payment_rail": "stripe_card",
                "cluster": "k8s-prod",
            }
        ],
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the alert was captured",
    )

    def generate_signature(self) -> str:
        """
        Generate a deterministic SHA-256 fingerprint for alert storm deduplication.

        Calculated across service_name, error_type, and the first 100 characters
        of error_message. This guarantees identical recurring failures within an alert
        storm map to the same deduplication key regardless of dynamic timestamps or PIDs.
        """
        clean_service = self.service_name.strip().lower()
        clean_type = (self.error_type or "").strip().lower()
        clean_msg = self.error_message.strip()[:100]

        hash_seed = f"{clean_service}:{clean_type}:{clean_msg}".encode()
        return hashlib.sha256(hash_seed).hexdigest()
