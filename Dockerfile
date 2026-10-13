FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY requirements.txt pyproject.toml /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and SDK
COPY src/ /app/src/
COPY sdk/ /app/sdk/

# Set environment
ENV PYTHONPATH=/app:/app/sdk/python
ENV HOME=/tmp
ENV CREWAI_STORAGE_DIR=/tmp/crewai_storage
ENV CREWAI_DISABLE_TELEMETRY=true

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
