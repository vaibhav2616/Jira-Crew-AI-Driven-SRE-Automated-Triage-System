"""SRE Triage Client SDK for Universal Microservice Integration.

Easily integrate any Python microservice, distributed payment gateway,
or background worker with the Jira-CrewAI SRE Automated Triage System.
"""

from sre_triage_sdk.client import SRETriageClient, triage_on_failure

__all__ = [
    "SRETriageClient",
    "triage_on_failure",
]
