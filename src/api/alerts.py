"""Alert ingestion endpoint for SRE Automated Triage."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.adapters.alertmanager import AlertmanagerAdapter
from src.adapters.base import BaseAlertAdapter
from src.adapters.generic import GenericAlertAdapter
from src.adapters.sentry import SentryAdapter
from src.api.deps import get_triage_service
from src.infrastructure.exceptions import JiraAPIError
from src.schemas.alert import AlertTriageResponse, IncomingAlert
from src.services.triage_service import TriageService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Alerts"])


@router.post(
    "/alerts",
    response_model=AlertTriageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest incoming SRE alert and trigger triage",
    description=(
        "Accepts a generic alert JSON payload from monitoring/alerting systems "
        "(e.g., Datadog, Prometheus Alertmanager, PagerDuty), orchestrates triage, "
        "and creates a corresponding Atlassian Jira issue."
    ),
)
async def ingest_alert(
    alert: IncomingAlert,
    triage_service: TriageService = Depends(get_triage_service),  # noqa: B008
) -> AlertTriageResponse:
    """
    Ingest an incoming alert, initiate triage processing, and create a Jira ticket.

    Args:
        alert: Incoming alert payload with service_name, error_message, and raw_logs
        triage_service: Injected TriageService instance

    Returns:
        AlertTriageResponse containing the created ticket key and metadata
    """
    try:
        response = await triage_service.process_alert(alert)
        return response
    except JiraAPIError as err:
        logger.error("Jira API error during alert triage: %s", err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Failed to create Jira triage ticket",
                "jira_error": err.message,
                "jira_status_code": err.status_code,
            },
        ) from err
    except Exception as exc:
        logger.exception("Unexpected error processing alert for %s", alert.service_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during alert triage processing",
        ) from exc


@router.post(
    "/triage/ingest",
    response_model=AlertTriageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Universal ingestion endpoint for any distributed service or monitoring webhook",
    description=(
        "Universal ingestion endpoint. Automatically detects and adapts incoming incident payloads "
        "from Prometheus Alertmanager, Sentry, Datadog, or custom microservice JSON "
        "(such as Distributed Payment Gateways) and runs the multi-agent SRE crew triage pipeline."
    ),
)
async def ingest_universal_alert(
    raw_payload: dict[str, Any],
    triage_service: TriageService = Depends(get_triage_service),  # noqa: B008
) -> AlertTriageResponse:
    """
    Universal ingestion endpoint for any distributed system or observability webhook.

    Args:
        raw_payload: Arbitrary JSON payload from application or monitoring platform
        triage_service: Injected TriageService instance

    Returns:
        AlertTriageResponse containing ticket key, triage analysis, and runbook
    """
    # 1. Automatic Adapter Selection
    adapter: BaseAlertAdapter
    if "alerts" in raw_payload and isinstance(raw_payload["alerts"], list):
        adapter = AlertmanagerAdapter()
    elif any(k in raw_payload for k in ["project_slug", "culprit", "event_id"]):
        adapter = SentryAdapter()
    else:
        adapter = GenericAlertAdapter()

    universal_alert = adapter.adapt(raw_payload)

    try:
        response = await triage_service.process_alert(universal_alert)
        return response
    except JiraAPIError as err:
        logger.error("Jira API error during universal alert triage: %s", err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Failed to create Jira triage ticket",
                "jira_error": err.message,
                "jira_status_code": err.status_code,
            },
        ) from err
    except Exception as exc:
        logger.exception(
            "Unexpected error processing universal alert for %s",
            universal_alert.service_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during alert triage processing",
        ) from exc
