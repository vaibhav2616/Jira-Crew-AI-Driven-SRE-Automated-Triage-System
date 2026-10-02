"""Main FastAPI application definition for AI-driven SRE Automated Triage System."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.alerts import router as alerts_router
from src.api.health import router as health_router
from src.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
)
logger = logging.getLogger("sre-automated-triage")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown hooks."""
    settings = get_settings()
    logger.info("Initializing AI-driven SRE Automated Triage System")
    logger.info("Jira Target Domain: %s", settings.JIRA_DOMAIN)
    logger.info("Jira Project Key: %s", settings.JIRA_PROJECT_KEY)
    logger.info(
        "Gemini AI API configured: %s", "Yes" if settings.GEMINI_API_KEY else "No"
    )
    yield
    logger.info("Shutting down AI-driven SRE Automated Triage System")


def create_app() -> FastAPI:
    """Application factory for FastAPI microservice."""
    app = FastAPI(
        title="AI-driven SRE Automated Triage System",
        description=(
            "An enterprise microservice for receiving production alerts, performing "
            "automated triage analysis, and synchronizing with Atlassian Jira."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health and diagnostics routes
    app.include_router(health_router)

    # V1 API Routes
    app.include_router(alerts_router, prefix="/api/v1")

    @app.get("/", tags=["Root"])
    async def root() -> dict[str, Any]:
        """Service discovery and info endpoint."""
        return {
            "service": "AI-driven SRE Automated Triage System",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/healthz",
            "endpoints": {
                "ingest_alert": "POST /api/v1/alerts",
            },
        }

    return app


app = create_app()
