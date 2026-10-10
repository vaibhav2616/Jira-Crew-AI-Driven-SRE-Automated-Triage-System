"""CrewAI agent definitions for collaborative SRE incident triage."""

from typing import Any

from crewai import LLM, Agent


def create_sre_agents(llm: LLM | None = None) -> dict[str, Agent]:
    """
    Instantiate the 4 collaborative SRE agents comprising the virtual triage response team.

    Args:
        llm: Configured CrewAI LLM instance (Gemini, Ollama, Groq, etc.)

    Returns:
        Dictionary mapping agent roles to instantiated Agent instances.
    """
    agent_kwargs: dict[str, Any] = {"verbose": False}
    if llm is not None:
        agent_kwargs["llm"] = llm

    commander = Agent(
        role="Frontline Incident Triage Commander",
        goal="Evaluate incoming alert signals, assess customer and transaction SLA impact, classify incident severity (Sev-1 to Sev-4), and coordinate triage response.",
        backstory=(
            "You are a battle-tested Senior SRE Incident Commander with 15+ years of experience managing "
            "high-throughput distributed microservices. You cut through alarm fatigue, evaluate business blast "
            "radius, and ensure engineering teams remain focused on genuine customer disruptions."
        ),
        **agent_kwargs,
    )

    forensics = Agent(
        role="Observability & Telemetry Forensics Specialist",
        goal="Analyze raw logs, stack traces, database pool metrics, and distributed trace headers to isolate anomalous failure patterns.",
        backstory=(
            "You are a forensic observability expert specializing in Linux internals, connection pooling, "
            "and distributed tracing. You can extract the critical error signature, saturated resource, "
            "or deadlock chain from noisy telemetry data."
        ),
        **agent_kwargs,
    )

    rca_architect = Agent(
        role="Principal Root Cause Analyst & Distributed Systems Diagnostician",
        goal="Formulate the definitive Root Cause Analysis (RCA) by linking observability anomalies to architectural root causes.",
        backstory=(
            "You are a Principal Distributed Systems Architect who has designed resilient financial, "
            "payment processing, and cloud-native systems. You never settle for surface symptoms like "
            "'database connection timed out'—you deduce why connections were exhausted (such as uncommitted "
            "transactions holding row locks during concurrent requests)."
        ),
        **agent_kwargs,
    )

    runbook_engineer = Agent(
        role="SRE Automation & Remediation Engineer",
        goal="Generate actionable, copy-pasteable, step-by-step mitigation commands, rollback instructions, and preventative measures for on-call responders.",
        backstory=(
            "You are an automated operations and infrastructure reliability engineer. You write clear, "
            "foolproof, and battle-tested runbooks containing specific kubectl commands, SQL diagnostic "
            "queries, and rollback steps with safety guardrails."
        ),
        **agent_kwargs,
    )

    return {
        "commander": commander,
        "forensics": forensics,
        "rca_architect": rca_architect,
        "runbook_engineer": runbook_engineer,
    }
