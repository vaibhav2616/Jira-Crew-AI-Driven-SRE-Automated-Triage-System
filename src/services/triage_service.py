"""Triage orchestration service for processing incoming SRE alerts."""

import logging
from typing import Any

import httpx

from src.infrastructure.exceptions import JiraAPIError
from src.infrastructure.jira_client import JiraClient
from src.infrastructure.protocols import LLMClientProtocol, RedisClientProtocol
from src.schemas.alert import AlertTriageResponse, IncomingAlert
from src.schemas.universal_alert import UniversalAlertPayload

logger = logging.getLogger(__name__)


class TriageService:
    """
    Orchestrates alert triage workflows using Redis deduplication,
    Multi-Agent CrewAI reasoning / Gemini LLM analysis, and Atlassian Jira issue tracking.
    """

    def __init__(
        self,
        jira_client: JiraClient,
        llm_client: LLMClientProtocol,
        redis_client: RedisClientProtocol,
        crew_engine: Any = None,
    ) -> None:
        """
        Initialize the triage service with Jira, LLM, Redis, and optional CrewAI engine.

        Args:
            jira_client: JiraClient instance for issue tracking operations
            llm_client: LLM client implementing LLMClientProtocol for structured triage reasoning
            redis_client: Redis client implementing RedisClientProtocol for deduplication
            crew_engine: Optional SREIncidentCrew instance for multi-agent triage
        """
        self.jira_client = jira_client
        self.llm_client = llm_client
        self.redis_client = redis_client
        self.crew_engine = crew_engine

    async def process_alert(
        self, alert: IncomingAlert | UniversalAlertPayload
    ) -> AlertTriageResponse:
        """
        Process an incoming alert with deduplication protection, multi-agent CrewAI/LLM diagnosis, and Jira ticketing.

        Args:
            alert: Validated IncomingAlert or UniversalAlertPayload

        Returns:
            AlertTriageResponse containing ticket key, status, summary, and structured triage

        Raises:
            JiraAPIError: If Jira rejects the ticket creation request
            httpx.TimeoutException: If the Jira API times out (propagated from JiraClient)
        """
        # 1. Alert Deduplication Guardrail (Check Redis)
        signature = alert.generate_signature()
        existing_ticket = await self.redis_client.check_and_set_dedup(
            signature, ttl_seconds=900
        )

        if existing_ticket:
            logger.warning(
                "Alert storm suppressed for service '%s' (signature: %s). "
                "Halting pipeline and linking to existing ticket %s.",
                alert.service_name,
                signature,
                existing_ticket,
            )
            return AlertTriageResponse(
                status="deduplicated",
                issue_key=existing_ticket,
                issue_id=None,
                issue_url=f"{self.jira_client.base_url}/browse/{existing_ticket}",
                summary=f"[DEDUPLICATED] Alert for {alert.service_name} already tracked under {existing_ticket}",
                triage_result=None,
            )

        logger.info(
            "Cache MISS for signature %s. Initiating multi-agent SRE triage for service '%s'",
            signature,
            alert.service_name,
        )

        # 2. Execute Multi-Agent CrewAI or LLM incident diagnosis pipeline
        if self.crew_engine is not None:
            # Ensure payload is in UniversalAlertPayload format for CrewAI
            if not isinstance(alert, UniversalAlertPayload):
                universal_alert = UniversalAlertPayload(
                    service_name=alert.service_name,
                    error_message=alert.error_message,
                    raw_logs=alert.raw_logs,
                )
            else:
                universal_alert = alert

            triage_result = await self.crew_engine.execute_triage(universal_alert)
        else:
            triage_result = await self.llm_client.analyze_alert(
                service_name=alert.service_name,
                error_message=alert.error_message,
                raw_logs=alert.raw_logs
                if isinstance(alert.raw_logs, dict)
                else {"logs": alert.raw_logs},
            )

        # 3. Dynamically construct Jira ticket summary:
        # [{triage_result.severity_level}] Triage: {alert.service_name} - {alert.error_message[:50]}
        summary = f"[{triage_result.severity_level}] Triage: {alert.service_name} - {alert.error_message[:50]}"

        # 4. Format Jira description with Multi-Agent SRE findings
        description = self.jira_client.build_adf_description(
            root_cause_analysis=triage_result.root_cause_analysis,
            remediation_runbook=triage_result.remediation_runbook,
            error_message=alert.error_message,
            raw_logs=alert.raw_logs
            if isinstance(alert.raw_logs, dict)
            else {"logs": alert.raw_logs},
            impact_assessment=getattr(triage_result, "impact_assessment", None),
            anomalies_detected=getattr(triage_result, "anomalies_detected", None),
            rollback_guidance=getattr(triage_result, "rollback_guidance", None),
            preventative_measures=getattr(triage_result, "preventative_measures", None),
            trace_id=getattr(alert, "trace_id", None),
        )

        logger.info(
            "Creating Jira ticket with summary '%s' for '%s'",
            summary,
            alert.service_name,
        )

        # 5. Dispatch ticket creation to Jira REST API v3
        # Wrap network-level failures in JiraAPIError so the 502 boundary in alerts.py catches them
        try:
            ticket_data = await self.jira_client.create_ticket(
                summary=summary,
                description=description,
                issue_type="Task",
            )
        except httpx.RequestError as exc:
            logger.error(
                "Network timeout/connection error reaching Jira for service '%s': %s",
                alert.service_name,
                exc,
            )
            raise JiraAPIError(
                status_code=504,
                message=f"Jira API unreachable: {type(exc).__name__}: {exc}",
                response_body="",
                details={},
            ) from exc

        ticket_key = ticket_data.get("key", "UNKNOWN")

        # 6. Save deduplication signature to Redis with 15-minute TTL (900 seconds)
        await self.redis_client.set_dedup(signature, ticket_key, ttl_seconds=900)

        return AlertTriageResponse(
            status="ticket_created",
            issue_key=ticket_key,
            issue_id=str(ticket_data.get("id")) if ticket_data.get("id") else None,
            issue_url=ticket_data.get("self"),
            summary=summary,
            triage_result=triage_result,
        )
