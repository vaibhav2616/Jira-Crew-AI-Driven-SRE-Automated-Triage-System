"""CrewAI Task specifications for sequential SRE incident investigation."""

from crewai import Agent, Task

from src.schemas.triage_result import CrewSRETriageResult


def create_sre_tasks(agents: dict[str, Agent]) -> list[Task]:
    """
    Construct the sequential task pipeline for the virtual SRE crew.

    Args:
        agents: Dictionary of instantiated CrewAI agents.

    Returns:
        List of Tasks ordered for sequential execution.
    """
    commander = agents["commander"]
    forensics = agents["forensics"]
    rca_architect = agents["rca_architect"]
    runbook_engineer = agents["runbook_engineer"]

    # Task 1: Triage and Severity Classification
    triage_task = Task(
        description=(
            "Review the incoming incident alert payload:\n"
            "Impacted Service: {service_name}\n"
            "Environment: {environment}\n"
            "Error Message: {error_message}\n"
            "Error Type: {error_type}\n"
            "Context Tags: {tags}\n\n"
            "1. Evaluate user and transaction impact on {service_name}.\n"
            "2. Classify the severity strictly as 'High', 'Medium', or 'Low' "
            "(mapped to Sev-1/Sev-2 for High, Sev-3 for Medium, Sev-4 for Low).\n"
            "3. State a concise impact assessment statement."
        ),
        expected_output="A concise impact statement and classified severity level (High, Medium, or Low).",
        agent=commander,
    )

    # Task 2: Deep Forensic Telemetry Analysis
    forensic_task = Task(
        description=(
            "Perform in-depth telemetry forensics on the alert telemetry:\n"
            "Service: {service_name}\n"
            "Diagnostic Raw Logs:\n{raw_logs}\n"
            "System Metrics Snapshot:\n{metrics}\n"
            "Distributed Trace ID: {trace_id}\n\n"
            "1. Identify anomalies in connection counts, memory, latencies, or error rates.\n"
            "2. Extract failing code paths, SQL queries, or third-party API endpoints.\n"
            "3. Produce a bulleted list of isolated anomalous signals."
        ),
        expected_output="A bulleted list of isolated forensic anomalies and telemetry clues.",
        agent=forensics,
    )

    # Task 3: Root Cause Analysis
    rca_task = Task(
        description=(
            "Using the telemetry anomalies from the forensics specialist, determine the definitive root cause:\n"
            "Service: {service_name}\n"
            "Error: {error_message}\n\n"
            "Explain *why* the failure occurred at an architectural level (e.g., connection pool starvation, "
            "uncommitted database transactions holding exclusive locks, network timeouts, or circuit breaker trips). "
            "Be precise, objective, and evidence-backed."
        ),
        expected_output="A concise, highly technical Root Cause Analysis (RCA) paragraph explaining the exact system failure.",
        agent=rca_architect,
    )

    # Task 4: Actionable Runbook and Remediation Plan
    remediation_task = Task(
        description=(
            "Based on the Root Cause Analysis, draft a production-ready SRE incident package:\n"
            "Service: {service_name}\n\n"
            "1. Step-by-step remediation runbook with exact copy-pasteable CLI / SQL commands.\n"
            "2. Rollback instructions if this incident could be caused by a bad deployment.\n"
            "3. Long-term preventative measures to prevent recurrence.\n"
            "Output must strictly conform to the CrewSRETriageResult schema."
        ),
        expected_output="A complete, structured incident response containing root_cause_analysis, severity_level, remediation_runbook, and preventative_measures.",
        output_pydantic=CrewSRETriageResult,
        agent=runbook_engineer,
    )

    return [triage_task, forensic_task, rca_task, remediation_task]
