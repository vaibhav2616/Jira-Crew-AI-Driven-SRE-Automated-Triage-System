"""Extended structured result schemas for Multi-Agent CrewAI SRE Triage."""

from pydantic import Field

from src.schemas.alert import LLMTriageResult


class CrewSRETriageResult(LLMTriageResult):
    """
    Comprehensive triage analysis result produced by the collaborative SRE Crew.
    Extends LLMTriageResult for full backward compatibility.
    """

    impact_assessment: str = Field(
        default="",
        description="Assessment of user, transaction, and business SLA impact.",
        examples=[
            "~18% payment authorization degradation on Stripe rail; P99 latency up by 4.2x"
        ],
    )
    anomalies_detected: list[str] = Field(
        default_factory=list,
        description="Specific anomaly indicators isolated by the Telemetry Forensics agent.",
        examples=[
            "Active database connection pool saturated at 100/100 limit",
            "Slow query lock contention on 'payment_records' table (age > 28s)",
        ],
    )
    rollback_guidance: str | None = Field(
        default=None,
        description="Specific rollback instructions if the incident correlates with a recent release.",
        examples=["kubectl rollout undo deployment/payment-gateway -n production"],
    )
    preventative_measures: list[str] = Field(
        default_factory=list,
        description="Long-term architectural and monitoring improvements to prevent recurrence.",
        examples=[
            "Add PgBouncer transaction pooling proxy in front of primary Aurora cluster",
            "Implement circuit breaker pattern for external payment provider calls",
        ],
    )
