"""Custom exceptions for the SRE Automated Triage System."""

from typing import Any


class SRETriageException(Exception):
    """Base exception for all domain and infrastructure errors."""


class JiraAPIError(SRETriageException):
    """Raised when an interaction with the Atlassian Jira API fails."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(f"Jira API call failed [{status_code}]: {message}")
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        self.details = details or {}
