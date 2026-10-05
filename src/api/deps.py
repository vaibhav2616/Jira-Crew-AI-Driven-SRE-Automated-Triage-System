"""Dependency injection providers for FastAPI routes."""

from functools import lru_cache

from fastapi import Depends

from src.config import get_settings
from src.crew.sre_crew import SREIncidentCrew
from src.infrastructure.jira_client import JiraClient
from src.infrastructure.llm_client import LLMClient
from src.infrastructure.redis_client import RedisClient
from src.services.triage_service import TriageService


@lru_cache
def get_jira_client() -> JiraClient:
    """Provide a singleton JiraClient instance with connection reuse."""
    settings = get_settings()
    return JiraClient(
        domain=settings.JIRA_DOMAIN,
        email=settings.JIRA_EMAIL,
        api_token=settings.JIRA_API_TOKEN,
        project_key=settings.JIRA_PROJECT_KEY,
    )


@lru_cache
def get_llm_client() -> LLMClient:
    """Provide a singleton LLMClient instance."""
    settings = get_settings()
    return LLMClient(api_key=settings.GEMINI_API_KEY)


@lru_cache
def get_redis_client() -> RedisClient:
    """Provide a singleton RedisClient instance with connection pool reuse."""
    settings = get_settings()
    return RedisClient(redis_url=settings.REDIS_URL)


@lru_cache
def get_crew_engine() -> SREIncidentCrew:
    """Provide a singleton SREIncidentCrew instance for multi-agent triage."""
    from src.crew.sre_crew import SREIncidentCrew

    return SREIncidentCrew()


def get_triage_service(
    jira_client: JiraClient = Depends(get_jira_client),  # noqa: B008
    llm_client: LLMClient = Depends(get_llm_client),  # noqa: B008
    redis_client: RedisClient = Depends(get_redis_client),  # noqa: B008
    crew_engine: SREIncidentCrew = Depends(get_crew_engine),  # noqa: B008
) -> TriageService:
    """Provide a TriageService instance wired with Jira, LLM, Redis, and CrewAI engine."""
    return TriageService(
        jira_client=jira_client,
        llm_client=llm_client,
        redis_client=redis_client,
        crew_engine=crew_engine,
    )
