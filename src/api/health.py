"""Health and liveness probes for monitoring and container orchestration."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/healthz", summary="Health check endpoint")
async def health_check() -> dict[str, str]:
    """Return system health status."""
    return {"status": "ok", "service": "ai-driven-sre-automated-triage-system"}


@router.get("/livez", summary="Liveness check endpoint")
async def live_check() -> dict[str, str]:
    """Return liveness probe status."""
    return {"status": "alive"}
