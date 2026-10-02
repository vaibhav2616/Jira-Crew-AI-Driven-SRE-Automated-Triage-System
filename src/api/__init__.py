"""API package containing routing endpoints."""

from src.api.alerts import router as alerts_router
from src.api.health import router as health_router

__all__ = ["alerts_router", "health_router"]
