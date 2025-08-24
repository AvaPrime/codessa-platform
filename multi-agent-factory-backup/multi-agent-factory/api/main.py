from __future__ import annotations

"""
Multi‑Agent Factory API
-----------------------
A FastAPI service that:
  • Accepts tasks and publishes them to NATS JetStream (subject per role)
  • Tracks task lifecycle in Redis (queued → done)
  • Persists agent results to Postgres
  • Provides ingestion into the pgvector‑backed document store
  • Exposes a deep health endpoint that verifies schema + dependencies

Design notes
  • We keep a single shared NATS connection for the app process (reused across requests)
  • All Postgres operations in request handlers use psycopg *async* connections
  • Redis client is global and async (command calls are awaited)
  • Schema verification is done at startup and in /healthz/deps to prevent drift
"""

import os
import json
import asyncio
import datetime as dt
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import redis.asyncio as redis
import psycopg
import nats
from nats.js.api import StreamConfig

# Vector store ops. verify_schema() raises if DB schema doesn't match migrations.
from memory.vector_store import upsert_document, verify_schema

# -----------------------------------------------------------------------------
# Configuration (env‑driven with safe defaults for containerized envs)
# -----------------------------------------------------------------------------
NATS_URL: str = os.getenv("NATS_URL", "nats://nats:4222")
PG_URI: str = os.getenv("POSTGRES_URI", "postgresql://user:pass@db:5432/factory")
REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
TASK_TTL_SECONDS: int = 7 * 24 * 3600  # keep transient task status for 7 days

# A single global async Redis client; safe to share across tasks/requests.
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# We keep one NATS connection for the process. Reuse prevents churn and keeps
# JetStream consumers stable. It's established lazily and reused.
_nc: Optional[nats.NATS] = None

# Create the FastAPI app.
app = FastAPI(title="Multi-Agent Factory API")


# -----------------------------------------------------------------------------
# Request/response models
# -----------------------------------------------------------------------------
class Task(BaseModel):
    """Task envelope published to NATS. `role` determines the subject."""

    task_id: str
    role: str  # e.g., "doc_writer", "frontend_dev", ...
    payload: Dict[str, Any]


class IngestItem(BaseModel):
    """Document ingest payload for the vector store.

    If `doc_id` is omitted, the server generates one. The raw `text` is embedded
    and also stored in the documents.content column (enforced non‑blank).
    """

    text: str = Field(..., description="Raw text to embed/store")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    doc_id: Optional[str] = Field(default=None, description="Optional explicit ID")


# -----------------------------------------------------------------------------
# Application lifecycle hooks
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event() -> None:
    """Fail fast on schema drift, then bootstrap NATS in the background.

    We call verify_schema() synchronously here so the process dies early if the
    DB isn't migrated properly. NATS bootstrap is scheduled as a background task
    so startup isn't blocked by network I/O to the broker.
    """
    verify_schema()  # raises RuntimeError on mismatch

    # Kick off NATS/JetStream stream ensure + subscription setup without blocking.
    asyncio.create_task(_bootstrap_nats())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Gracefully drain the NATS connection on shutdown.

    We ignore drain errors to avoid masking the real shutdown reason.
    """
    global _nc
    try:
        if _nc and _nc.is_connected:
            await _nc.drain()
    except Exception:
        pass  # best‑effort drain only


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/")
async def root() -> Dict[str, Any]:
    """Lightweight liveness probe."""
    return {"status": "ok", "service": "api", "env": os.getenv("ENV", "dev")}


@app.get("/healthz/deps")
async def healthz_deps() -> JSONResponse | Dict[str, Any]:
    """Deep healthcheck covering schema + Postgres + Redis + NATS.

    Returns HTTP 200 when everything is OK, else HTTP 503 with diagnostics.
    """
    details, ok = await _check_dependencies()
    status = {"status": "ok" if ok else "degraded", "deps": details}
    if ok:
        return status
    return JSONResponse(status_code=503, content=status)


@app.post("/tasks")
async def submit_task(t: Task) -> Dict[str, Any]:
    """Accept a task, mark it queued in Redis, and publish to JetStream.

    Redis holds transient task status keyed by task_id. JetStream subject is
    namespaced by role (e.g., tasks.doc_writer). We reuse the shared NATS
    connection and publish with JetStream to ensure durability.
    """
    # Mark status queued in Redis with a TTL so old tasks expire automatically.
    await r.hset(f"task:{t.task_id}", mapping={"status": "queued", "role": t.role})
    await r.expire(f"task:{t.task_id}", TASK_TTL_SECONDS)

    # Publish to NATS JetStream (durable subject by role)
    nc = await _get_nats()
    js = nc.jetstream()
    subject = f"tasks.{t.role}"

    # Use model_dump() (pydantic v2) so the envelope is strictly JSON‑serializable.
    await js.publish(subject, json.dumps(t.model_dump()).encode("utf-8"))

    return {"accepted": True, "task_id": t.task_id, "role": t.role, "subject": subject}


@app.get("/tasks/{task_id}/status")
async def get_status(task_id: str) -> Dict[str, Any]:
    """Fetch transient task status from Redis.

    If the hash key is missing, we return 404 to signal unknown task.
    """
    data = await r.hgetall(f"task:{task_id}")
    if not data:
        raise HTTPException(status_code=404, detail="No status for this task")
    return {"task_id": task_id, **data}


@app.get("/results/{task_id}")
async def get_result(task_id: str) -> Dict[str, Any]:
    """Return the persisted result for a task from Postgres.

    Uses a short‑lived async connection. We serialize timestamps defensively.
    """
    async with await psycopg.AsyncConnection.connect(PG_URI) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT task_id, role, content, created_at FROM results WHERE task_id=%s",
                (task_id,),
            )
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Result not found")
            created_at = row[3]
            created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
            return {"task_id": row[0], "role": row[1], "content": row[2], "created_at": created_iso}


@app.get("/results")
async def list_results(limit: int = 50) -> list[Dict[str, Any]]:
    """List recent results with a small preview.

    We clamp `limit` into [1, 500] for safety.
    """
    limit = max(1, min(500, limit))
    async with await psycopg.AsyncConnection.connect(PG_URI) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT task_id, role, LEFT(content, 160) AS preview, created_at
                FROM results
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = await cur.fetchall()
            out: list[Dict[str, Any]] = []
            for rec in rows:
                created_at = rec[3]
                created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
                out.append({"task_id": rec[0], "role": rec[1], "preview": rec[2], "created_at": created_iso})
            return out


@app.post("/ingest")
async def ingest(item: IngestItem) -> Dict[str, Any]:
    """Ingest a document into the vector store.

    If `doc_id` is not supplied, we generate a stable, time‑based id. The vector
    store enforces non‑blank content and aligns with DB constraints.
    """
    try:
        doc_id = item.doc_id or f"doc_{dt.datetime.utcnow().isoformat()}"
        upsert_document(doc_id, item.text, item.metadata)
        return {"success": True, "doc_id": doc_id, "message": "Document ingested successfully"}
    except Exception as e:
        # Surface a precise error message while returning a 500 to clients.
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {e}")


# -----------------------------------------------------------------------------
# Internals (NATS bootstrap, dependency checks, shared connection management)
# -----------------------------------------------------------------------------
async def _get_nats() -> nats.NATS:
    """Get or establish the shared NATS connection.

    Reusing one connection avoids per‑request connects/drains and plays nicely
    with JetStream durable consumers.
    """
    global _nc
    if _nc and _nc.is_connected:
        return _nc
    _nc = await nats.connect(NATS_URL)
    return _nc


async def _bootstrap_nats() -> None:
    """Ensure JetStream streams exist and subscribe to results subjects.

    Stream creation is idempotent (errors are ignored if streams already exist).
    We then create a durable *push* consumer for `results.>` and register a
    callback that upserts results and flips task status to `done`.
    """
    nc = await _get_nats()
    js = nc.jetstream()

    # Ensure streams exist (safe to re‑run)
    try:
        await js.add_stream(StreamConfig(name="TASKS", subjects=["tasks.*"]))
    except Exception:
        pass  # already exists
    try:
        await js.add_stream(StreamConfig(name="RESULTS", subjects=["results.>"]))
    except Exception:
        pass  # already exists

    async def result_handler(msg: nats.aio.msg.Msg) -> None:
        """Handle agent result messages from any `results.*` subject.

        The payload is expected to be JSON with keys {task_id, role, result}.
        We upsert into Postgres and set Redis status to `done`. The handler is
        intentionally short and robust—malformed messages are ignored.
        """
        # Defensive decode/parse of message payload
        data = json.loads(msg.data.decode("utf-8"))
        task_id = data.get("task_id")
        role = data.get("role")
        content = data.get("result")
        if not task_id:
            return  # ignore malformed payloads

        # Persist (UPSERT) to Postgres keyed by task_id
        async with await psycopg.AsyncConnection.connect(PG_URI) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO results (task_id, role, content)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (task_id) DO UPDATE SET content = EXCLUDED.content
                    """,
                    (task_id, role, content),
                )
                await conn.commit()

        # Flip transient status in Redis to `done` with a finish timestamp
        finished = dt.datetime.utcnow().isoformat()
        await r.hset(f"task:{task_id}", mapping={"status": "done", "finished_at": finished})

    # Durable push consumer so we don't miss messages across restarts.
    # Using a queue group lets multiple API replicas share the load safely.
    await js.subscribe("results.>", durable="api_results", queue="api_results", cb=result_handler)
    print("[API] JetStream ready: streams ensured, subscribed to results.>")


async def _check_dependencies() -> Tuple[Dict[str, Any], bool]:
    """Probe schema, Redis, Postgres, and NATS.

    Returns a tuple of (details, ok). `details` maps component→"ok" or an error
    string. The overall flag aggregates individual checks.
    """
    details: Dict[str, Any] = {"schema": "ok", "postgres": "ok", "redis": "ok", "nats": "ok"}
    ok = True

    # Schema verification
    try:
        verify_schema()
    except Exception as e:
        details["schema"] = f"error: {e}"
        ok = False

    # Redis probe (PING)
    try:
        pong = await r.ping()
        if pong is not True:
            raise RuntimeError("redis ping failed")
    except Exception as e:
        details["redis"] = f"error: {e}"
        ok = False

    # Postgres probe (simple SELECT)
    try:
        async with await psycopg.AsyncConnection.connect(PG_URI, timeout=3) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
    except Exception as e:
        details["postgres"] = f"error: {e}"
        ok = False

    # NATS probe (flush ensures round‑trip to server)
    try:
        nc = await _get_nats()
        await nc.flush(timeout=1)
    except Exception as e:
        details["nats"] = f"error: {e}"
        ok = False

    return details, ok
