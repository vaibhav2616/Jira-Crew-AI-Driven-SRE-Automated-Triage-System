"""Asynchronous Atlassian Jira REST API v3 Client using httpx."""

import json
import logging
from typing import Any, Self

import httpx

from src.infrastructure.exceptions import JiraAPIError

logger = logging.getLogger(__name__)


class JiraClient:
    """
    Asynchronous client for interacting with Atlassian Jira REST API v3.
    Strictly structures payloads using the Atlassian Document Format (ADF) for descriptions.
    """

    def __init__(
        self,
        domain: str,
        email: str,
        api_token: str,
        project_key: str = "KAN",
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        """
        Initialize the Jira client.

        Args:
            domain: Jira domain (e.g. "your-name.atlassian.net" or full https URL)
            email: User account email for Basic Auth
            api_token: Atlassian API token
            project_key: Target Jira project key (default: "KAN")
            client: Optional pre-configured httpx.AsyncClient for connection pooling
            timeout: Request timeout in seconds
        """
        self.domain = domain.strip().rstrip("/")
        if not self.domain.startswith("http://") and not self.domain.startswith(
            "https://"
        ):
            self.base_url = f"https://{self.domain}"
        else:
            self.base_url = self.domain

        self.email = email
        self.api_token = api_token
        self.project_key = project_key
        self.timeout = timeout

        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    @property
    def auth(self) -> httpx.BasicAuth:
        """Return HTTP Basic Auth credentials."""
        return httpx.BasicAuth(username=self.email, password=self.api_token)

    @property
    def headers(self) -> dict[str, str]:
        """Return standard headers for Atlassian REST API v3 requests."""
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "AI-SRE-Automated-Triage/1.0",
        }

    @staticmethod
    def build_adf_description(
        text: str = "",
        root_cause_analysis: str | None = None,
        remediation_runbook: list[str] | None = None,
        error_message: str | None = None,
        raw_logs: dict[str, Any] | list[Any] | None = None,
        impact_assessment: str | None = None,
        anomalies_detected: list[str] | None = None,
        rollback_guidance: str | None = None,
        preventative_measures: list[str] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Convert text or structured Multi-Agent SRE triage outputs into Atlassian Document Format (ADF) v1.

        Args:
            text: Fallback plain text content.
            root_cause_analysis: LLM/Crew-diagnosed root cause explanation.
            remediation_runbook: Actionable steps for on-call responders.
            error_message: Original service alert error message.
            raw_logs: Diagnostic logs payload.
            impact_assessment: Business, user, and SLA impact summary.
            anomalies_detected: List of specific telemetry anomalies.
            rollback_guidance: Instructions for rolling back recent changes.
            preventative_measures: Long-term architectural recommendations.
            trace_id: Distributed trace identifier.

        Returns:
            Dictionary matching the ADF v1 JSON schema.
        """
        # If structured triage elements are provided, build rich ADF
        if (
            root_cause_analysis
            or remediation_runbook
            or impact_assessment
            or anomalies_detected
        ):
            content: list[dict[str, Any]] = []

            # 1. Executive Impact Assessment
            if impact_assessment:
                content.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [
                            {"type": "text", "text": "Incident Impact Assessment"}
                        ],
                    }
                )
                content.append(
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": impact_assessment}],
                    }
                )

            # 2. Root Cause Analysis section
            if root_cause_analysis:
                content.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Root Cause Analysis"}],
                    }
                )
                content.append(
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": root_cause_analysis}],
                    }
                )

            # 3. Telemetry Anomalies
            if anomalies_detected:
                content.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [
                            {"type": "text", "text": "Observed Telemetry Anomalies"}
                        ],
                    }
                )
                bullet_items = [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": anomaly}],
                            }
                        ],
                    }
                    for anomaly in anomalies_detected
                    if anomaly.strip()
                ]
                content.append({"type": "bulletList", "content": bullet_items})

            # 4. Remediation Runbook section
            if remediation_runbook:
                content.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Remediation Runbook"}],
                    }
                )
                list_items = [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": step}],
                            }
                        ],
                    }
                    for step in remediation_runbook
                    if step.strip()
                ]
                content.append(
                    {
                        "type": "orderedList",
                        "content": list_items,
                    }
                )

            # 5. Rollback Guidance
            if rollback_guidance:
                content.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Rollback Guidance"}],
                    }
                )
                content.append(
                    {
                        "type": "codeBlock",
                        "attrs": {"language": "bash"},
                        "content": [{"type": "text", "text": rollback_guidance}],
                    }
                )

            # 6. Preventative Measures
            if preventative_measures:
                content.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Preventative Measures"}],
                    }
                )
                prev_items = [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": item}],
                            }
                        ],
                    }
                    for item in preventative_measures
                    if item.strip()
                ]
                content.append({"type": "bulletList", "content": prev_items})

            # 7. Original Error Message & Trace ID
            if error_message or trace_id:
                content.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [
                            {"type": "text", "text": "Original Error & Telemetry"}
                        ],
                    }
                )
                desc_text = f"Error: {error_message}" if error_message else ""
                if trace_id:
                    desc_text += f"\nTrace ID: {trace_id}"
                content.append(
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": desc_text}],
                    }
                )

            # 8. Diagnostic Logs (Code block)
            if raw_logs:
                content.append(
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Diagnostic Logs"}],
                    }
                )
                formatted_logs = (
                    json.dumps(raw_logs, indent=2)
                    if isinstance(raw_logs, (dict, list))
                    else str(raw_logs)
                )
                content.append(
                    {
                        "type": "codeBlock",
                        "attrs": {"language": "json"},
                        "content": [{"type": "text", "text": formatted_logs}],
                    }
                )

            return {
                "version": 1,
                "type": "doc",
                "content": content,
            }

        # Fallback to plain text wrapping
        if not text:
            return {
                "version": 1,
                "type": "doc",
                "content": [],
            }

        return {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": text,
                        }
                    ],
                }
            ],
        }

    async def create_ticket(
        self,
        summary: str,
        description: str | dict[str, Any],
        issue_type: str = "Task",
    ) -> dict[str, Any]:
        """
        Create a new issue in Jira via REST API v3.

        Args:
            summary: Short summary / title of the issue
            description: Plain text or pre-formatted ADF dictionary
            issue_type: Jira issue type (default: "Task")

        Returns:
            Dict containing the created issue metadata (id, key, self)

        Raises:
            JiraAPIError: If the Jira API returns an error response
            httpx.RequestError: If network connectivity fails
        """
        url = f"{self.base_url}/rest/api/3/issue"

        if isinstance(description, dict) and description.get("type") == "doc":
            description_adf = description
        elif isinstance(description, str):
            description_adf = self.build_adf_description(text=description)
        else:
            description_adf = self.build_adf_description(text=str(description))

        payload = {
            "fields": {
                "project": {
                    "key": self.project_key,
                },
                "summary": summary,
                "issuetype": {
                    "name": issue_type,
                },
                "description": description_adf,
            }
        }

        logger.info(
            "Creating Jira ticket: project=%s, issue_type=%s, summary='%s'",
            self.project_key,
            issue_type,
            summary,
        )

        try:
            response = await self._client.post(
                url,
                json=payload,
                headers=self.headers,
                auth=self.auth,
            )
        except httpx.RequestError as exc:
            logger.error("Network error communicating with Jira at %s: %s", url, exc)
            raise

        if response.status_code != 201:
            error_details: dict[str, Any] = {}
            error_message = f"HTTP {response.status_code}"
            try:
                error_details = response.json()
                if error_details.get("errorMessages"):
                    error_message = "; ".join(error_details["errorMessages"])
                elif error_details.get("errors"):
                    error_message = str(error_details["errors"])
            except (ValueError, KeyError):
                error_message = response.text or error_message

            logger.error(
                "Jira ticket creation failed [%d]: %s",
                response.status_code,
                error_message,
            )
            raise JiraAPIError(
                status_code=response.status_code,
                message=error_message,
                response_body=response.text,
                details=error_details,
            )

        data: dict[str, Any] = response.json()
        logger.info(
            "Successfully created Jira issue: key=%s, id=%s",
            data.get("key"),
            data.get("id"),
        )
        return data

    async def aclose(self) -> None:
        """Close the underlying HTTP client if internally managed."""
        if not self._external_client:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
