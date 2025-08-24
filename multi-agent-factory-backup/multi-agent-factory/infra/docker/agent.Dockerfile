# =========================
# Stage 1 — build wheels
# =========================
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /wheels

# build deps only for compiling any native wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential gcc curl \
    && rm -rf /var/lib/apt/lists/*

# install shared requirements to wheels (best cache leverage)
COPY agents/requirements.txt /tmp/requirements.txt
RUN pip wheel --wheel-dir /wheels -r /tmp/requirements.txt


# =========================
# Stage 2 — runtime
# =========================
FROM python:3.11-slim AS runtime

ARG AGENT_ROLE
ENV AGENT_ROLE=${AGENT_ROLE}

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# tiny debug tooling; remove if you want ultraminimal
RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

# non-root
RUN useradd -u 10002 -ms /bin/bash agentuser

WORKDIR /app

# install shared deps from wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*.whl

# copy application code (ensure destinations end with /)
COPY agents/      ./agents/
COPY memory/      ./memory/
COPY config/      ./config/

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

# permissions
RUN chown -R agentuser:agentuser /app
USER agentuser

# optional healthcheck (enable if you like; tweak target endpoint or script)
# HEALTHCHECK --interval=20s --timeout=3s --retries=5 \
#   CMD python - <<'PY' || exit 1
# import importlib, os, sys
# role = os.environ.get("AGENT_ROLE", "")
# sys.exit(0 if role and (importlib.util.find_spec(f"agents.{role}.agent") is not None) else 1)
# PY

# default command: run the agent
CMD ["bash", "-lc", "exec python -u agents/${AGENT_ROLE}/agent.py"]
