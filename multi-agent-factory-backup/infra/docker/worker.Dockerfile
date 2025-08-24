FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY orchestrator/ ./orchestrator/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash worker
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from orchestrator.temporal_client import temporal_manager; asyncio.run(temporal_manager.connect())" || exit 1

CMD ["python", "-m", "orchestrator.worker"]