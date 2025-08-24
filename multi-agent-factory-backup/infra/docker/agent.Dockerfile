# =========================
# Stage 1 — build wheels
# =========================
FROM python:3.11-slim AS builder

# Security: Run as non-root during build
RUN groupadd -r builduser && useradd -r -g builduser builduser

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /wheels

# build deps only for compiling any native wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential gcc curl ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install shared requirements to wheels (best cache leverage)
COPY agents/requirements.txt /tmp/requirements.txt
RUN pip wheel --wheel-dir /wheels -r /tmp/requirements.txt

# Change ownership to builduser
RUN chown -R builduser:builduser /wheels
USER builduser


# =========================
# Stage 2 — runtime
# =========================
FROM python:3.11-slim AS runtime

ARG AGENT_ROLE
ENV AGENT_ROLE=${AGENT_ROLE}

# Security and performance environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1

# Install minimal runtime dependencies with security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with specific UID/GID for security
RUN groupadd -r -g 10002 agentuser && \
    useradd -r -u 10002 -g agentuser -m -s /bin/bash agentuser

WORKDIR /app

# install shared deps from wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*.whl

# copy application code (ensure destinations end with /)
COPY agents/      ./agents/
COPY memory/      ./memory/
COPY config/      ./config/

# copy and set up entrypoint script
COPY infra/docker/agent-entrypoint.sh /usr/local/bin/agent-entrypoint.sh
RUN chmod +x /usr/local/bin/agent-entrypoint.sh

# ensure these are packages even if __init__.py was forgotten
RUN set -eux; \
  for d in agents memory config; do \
    [ -d "$d" ] && [ ! -f "$d/__init__.py" ] && touch "$d/__init__.py" || true; \
  done

# install role-specific requirements if present (kept *after* code copy for better cache on role switches)
RUN if [ -n "${AGENT_ROLE}" ] && [ -f "/app/agents/${AGENT_ROLE}/requirements.txt" ]; then \
      pip install --no-cache-dir --prefer-binary -r "/app/agents/${AGENT_ROLE}/requirements.txt"; \
    fi

# sanity check: fail early if role not provided or script missing
RUN set -eux; \
  test -n "${AGENT_ROLE}" || (echo "AGENT_ROLE not set" && exit 64); \
  test -f "agents/${AGENT_ROLE}/agent.py" || (echo "agents/${AGENT_ROLE}/agent.py not found" && ls -R agents && exit 66)

# Security: Create additional directories and set permissions
RUN mkdir -p /app/logs /app/tmp && \
    chown -R agentuser:agentuser /app

# Switch to non-root user
USER agentuser

# Enhanced healthcheck with proper agent validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "\
import importlib.util, os, sys, json; \
role = os.environ.get('AGENT_ROLE', ''); \
if not role: sys.exit(1); \
spec = importlib.util.find_spec(f'agents.{role}.agent'); \
if not spec: sys.exit(1); \
print(json.dumps({'status': 'healthy', 'agent_role': role, 'timestamp': __import__('time').time()})); \
sys.exit(0)" || exit 1

# Use entrypoint script for proper initialization and signal handling
ENTRYPOINT ["/usr/local/bin/agent-entrypoint.sh"]
CMD []
