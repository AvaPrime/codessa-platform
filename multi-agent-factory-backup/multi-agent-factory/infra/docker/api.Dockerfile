# =========================
# Stage 1 — Build wheels
# =========================
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /wheels

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /tmp/requirements.txt
RUN pip wheel --wheel-dir /wheels -r /tmp/requirements.txt


# =========================
# Stage 2 — Runtime
# =========================
FROM python:3.11-slim AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    WORKERS=2 \
    THREADS=1 \
    TIMEOUT=60 \
    KEEP_ALIVE=5

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -u 10001 -ms /bin/bash appuser

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*.whl

# ✅ Destination ends with / to satisfy multiple-source COPY rule
COPY api/ ./ 
COPY orchestrator/ ./orchestrator/
COPY memory/ ./memory/
COPY llm/ ./llm/
COPY config/ ./config/

RUN set -eux; \
    for d in memory llm orchestrator config; do \
      [ -d "$d" ] && [ ! -f "$d/__init__.py" ] && touch "$d/__init__.py" || true; \
    done

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null || exit 1

CMD ["bash", "-lc", "\
  exec gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --workers ${WORKERS} \
    --threads ${THREADS} \
    --timeout ${TIMEOUT} \
    --keep-alive ${KEEP_ALIVE} \
    --access-logfile - \
    --error-logfile - \
"]
