"""Example integration: Distributed Payment Gateway reporting to SRE Automated Triage.

Demonstrates how any external microservice, distributed payment system,
or e-commerce platform integrates with the Jira-CrewAI SRE Automated Triage System.
"""

import asyncio
import logging
import os
import sys

# Add project root to sys.path so sdk can be imported directly
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk", "python"))
)

from typing import Any

from sre_triage_sdk import SRETriageClient, triage_on_failure

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s"
)
logger = logging.getLogger("payment_gateway_demo")

TRIAGE_ENDPOINT = os.getenv(
    "SRE_TRIAGE_ENDPOINT", "http://localhost:8000/api/v1/triage/ingest"
)
sre_client = SRETriageClient(endpoint=TRIAGE_ENDPOINT)


# Scenario 1: Function decorated with @triage_on_failure
@triage_on_failure(service_name="payment-gateway", endpoint=TRIAGE_ENDPOINT)
def process_credit_card_charge(
    order_id: str, amount_cents: int, idempotency_key: str
) -> dict[str, Any]:
    """
    Simulates a payment processing failure due to PostgreSQL pool starvation.
    """
    logger.info(
        "Attempting payment for order %s (amount: $%0.2f)...",
        order_id,
        amount_cents / 100,
    )
    # Simulate database connection pool starvation under high load
    raise ConnectionError(
        "Postgres connection pool exhausted: active_connections=100/100, "
        "timeout waiting for idle socket checkout after 15000ms"
    )


# Scenario 2: Manual capture with custom telemetry and metrics
async def process_stripe_webhook_settlement(event_id: str, trace_id: str) -> None:
    """
    Simulates third-party gateway 504 gateway timeout and manual incident dispatch.
    """
    logger.info("Processing Stripe webhook settlement event: %s", event_id)
    try:
        # Simulate third-party upstream timeout
        raise TimeoutError(
            "Stripe API gateway timeout: upstream 504 Gateway Timeout on /v1/charges/settle"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Payment rail settlement failed. Forwarding telemetry to SRE Triage..."
        )
        result = await sre_client.async_report_incident(
            service_name="payment-gateway",
            error_message=str(exc),
            error_type="UpstreamPaymentRailTimeout",
            raw_logs={
                "event_id": event_id,
                "payment_provider": "stripe",
                "attempt_number": 3,
                "endpoint": "https://api.stripe.com/v1/charges/settle",
            },
            metrics={
                "upstream_latency_ms": 30045,
                "p99_latency_ms": 12500,
                "circuit_breaker_state": "half-open",
            },
            trace_id=trace_id,
            tags={
                "payment_rail": "stripe_ach",
                "region": "us-east-1",
                "priority": "high",
            },
        )
        logger.info("SRE Triage Dispatch Result: %s", result)


def run_demo() -> None:
    print("=================================================================")
    print("  DISTRIBUTED PAYMENT GATEWAY -> SRE AUTOMATED TRIAGE DEMO")
    print("=================================================================")
    print(f"Targeting SRE Triage API at: {TRIAGE_ENDPOINT}\n")

    # 1. Trigger Scenario 1: Decorator caught failure
    print("[1] Simulating Payment Processing Pool Starvation (Decorator Flow)...")
    try:
        process_credit_card_charge(
            order_id="ord_998124",
            amount_cents=14999,
            idempotency_key="idemp_a94b81c2",
        )
    except ConnectionError:
        print(
            " -> Caught expected failure in application. SRE incident dispatched automatically.\n"
        )

    # 2. Trigger Scenario 2: Async Webhook Settlement Timeout
    print("[2] Simulating Stripe Gateway 504 Timeout (Direct Client SDK Flow)...")
    asyncio.run(
        process_stripe_webhook_settlement(
            event_id="evt_stripe_88349",
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        )
    )

    print("\n=================================================================")
    print("  Demo Complete: Incidents dispatched to SRE Triage microservice.")
    print("=================================================================")


if __name__ == "__main__":
    run_demo()
