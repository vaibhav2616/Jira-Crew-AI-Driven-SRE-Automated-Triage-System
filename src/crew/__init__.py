"""CrewAI Multi-Agent SRE Incident Triage Engine."""

import os

# Ensure CrewAI storage paths resolve to writable directories across sandbox/container environments
os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai_storage")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

from src.crew.agents import create_sre_agents
from src.crew.sre_crew import SREIncidentCrew
from src.crew.tasks import create_sre_tasks

__all__ = [
    "SREIncidentCrew",
    "create_sre_agents",
    "create_sre_tasks",
]
