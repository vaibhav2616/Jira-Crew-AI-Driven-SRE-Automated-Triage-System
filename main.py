"""Entrypoint to run the Uvicorn server for the SRE Automated Triage microservice."""

import uvicorn
from src.config import get_settings
from src.main import app

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
