"""Unit tests for Universal Alert Schema and Payload Adapters."""

from src.adapters.alertmanager import AlertmanagerAdapter
from src.adapters.generic import GenericAlertAdapter
from src.adapters.sentry import SentryAdapter
from src.schemas.universal_alert import UniversalAlertPayload


def test_universal_alert_signature_generation() -> None:
    """Verify deterministic SHA-256 signature generation for deduplication."""
    alert1 = UniversalAlertPayload(
        service_name="payment-gateway",
        environment="production",
        error_message="Postgres pool exhausted after 15000ms",
        error_type="ConnectionStarvation",
        raw_logs={"active": 100},
    )
    alert2 = UniversalAlertPayload(
        service_name="payment-gateway",
        environment="production",
        error_message="Postgres pool exhausted after 15000ms",
        error_type="ConnectionStarvation",
        raw_logs={"active": 100, "retry": 2},
    )
    alert3 = UniversalAlertPayload(
        service_name="auth-service",
        environment="production",
        error_message="Postgres pool exhausted after 15000ms",
        error_type="ConnectionStarvation",
    )

    sig1 = alert1.generate_signature()
    sig2 = alert2.generate_signature()
    sig3 = alert3.generate_signature()

    assert len(sig1) == 64
    assert sig1 == sig2
    assert sig1 != sig3  # Different service name
    assert sig1.isalnum()


def test_alertmanager_adapter() -> None:
    """Verify Alertmanager JSON is correctly adapted to UniversalAlertPayload."""
    adapter = AlertmanagerAdapter()
    raw_payload = {
        "status": "firing",
        "groupLabels": {"alertname": "High5xxRate"},
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "High5xxRate",
                    "service": "checkout-api",
                    "environment": "production",
                    "severity": "critical",
                    "trace_id": "trace-99128",
                },
                "annotations": {
                    "summary": "Elevated 5xx HTTP error rate (>15%)",
                    "description": "Checkout API returning 500 on /pay endpoint",
                },
                "generatorURL": "http://prometheus:9090/graph",
            }
        ],
    }

    alert = adapter.adapt(raw_payload)
    assert alert.service_name == "checkout-api"
    assert alert.environment == "production"
    assert "Checkout API returning 500" in alert.error_message
    assert alert.error_type == "High5xxRate"
    assert alert.trace_id == "trace-99128"
    assert alert.metrics["status"] == "firing"


def test_sentry_adapter() -> None:
    """Verify Sentry webhook JSON is correctly adapted to UniversalAlertPayload."""
    adapter = SentryAdapter()
    raw_payload = {
        "project_slug": "payment-gateway",
        "event": {
            "title": "psycopg2.OperationalError: connection pool exhausted",
            "culprit": "payment.services.charge_customer",
            "type": "error",
            "environment": "production",
            "tags": [
                ["environment", "production"],
                ["trace_id", "sentry-trace-1234"],
                ["payment_rail", "stripe_cards"],
            ],
            "contexts": {"trace": {"trace_id": "sentry-trace-1234"}},
        },
    }

    alert = adapter.adapt(raw_payload)
    assert alert.service_name == "payment-gateway"
    assert alert.environment == "production"
    assert "connection pool exhausted" in alert.error_message
    assert "payment.services.charge_customer" in alert.error_message
    assert alert.trace_id == "sentry-trace-1234"
    assert alert.tags["payment_rail"] == "stripe_cards"


def test_generic_adapter_with_payment_gateway_payload() -> None:
    """Verify generic/custom microservice payload adapts properly."""
    adapter = GenericAlertAdapter()
    raw_payload = {
        "service": "distributed-payment-processor",
        "error": "Deadlock detected in account balance debit row lock",
        "exception_type": "DeadlockError",
        "env": "production",
        "trace_id": "txn-trace-77441",
        "logs": {"account_id": "acc_8841", "balance": 1500},
        "metrics": {"p99_ms": 4200, "active_txns": 85},
        "tags": {"datacenter": "us-east"},
    }

    alert = adapter.adapt(raw_payload)
    assert alert.service_name == "distributed-payment-processor"
    assert alert.environment == "production"
    assert alert.error_type == "DeadlockError"
    assert "Deadlock detected" in alert.error_message
    assert alert.trace_id == "txn-trace-77441"
    assert alert.metrics["active_txns"] == 85
    assert alert.tags["datacenter"] == "us-east"
