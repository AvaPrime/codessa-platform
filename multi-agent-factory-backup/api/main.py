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

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

# Import our auth and database modules
from auth import (
    get_current_user, require_scope, User, create_access_token,
    sign_task_envelope, verify_task_envelope, blacklist_token,
    generate_nats_hmac, verify_nats_hmac
)
from database import get_db, get_redis
from user_service import UserService, RoleService
from models import (
    LoginRequest, TokenResponse, UserCreate, UserUpdate, UserResponse,
    PasswordChange, RoleCreate, RoleUpdate, RoleResponse
)
from config.schemas.message_handler import ProductionMessageHandler
from config.schemas.task_message import TaskMessage, TaskPayload
from config.schemas.messages import MessageType
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
_message_handler: Optional[ProductionMessageHandler] = None

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
    """Initialize database, verify schema, and bootstrap NATS.

    We initialize the database tables first, then verify schema to ensure
    everything is properly set up. NATS bootstrap is scheduled as a background
    task so startup isn't blocked by network I/O to the broker.
    """
    from database import create_tables, check_db_health
    
    # Initialize database tables
    try:
        await create_tables()
        print("Database tables initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise
    
    # Verify database health
    try:
        await check_db_health()
        print("Database health check passed")
    except Exception as e:
        print(f"Database health check failed: {e}")
        raise
    
    # Verify vector store schema
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
@require_scope("task:create")
async def create_task(
    request: TaskSubmissionRequest,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """Submit a task for processing with Temporal orchestration."""
    
    task_id = request.task_id or f"{request.role}-{dt.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
    
    try:
        # Create Temporal task request
        task_request = TaskRequest(
            task_id=task_id,
            role=request.role,
            payload=request.payload,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds or 300,
            retry_attempts=3,
            user_id=current_user.user_id
        )
        
        # Start Temporal workflow
        workflow_id = await temporal_manager.execute_task_workflow(task_request)
        
        # Track in Redis for quick status checks
        await redis_client.hset(
            f"task:{task_id}",
            mapping={
                "status": "queued",
                "role": request.role,
                "workflow_id": workflow_id,
                "user_id": current_user.user_id,
                "created_at": dt.datetime.utcnow().isoformat(),
                "priority": str(request.priority)
            }
        )
        await redis_client.expire(f"task:{task_id}", 86400)  # 24h TTL
        
        return JSONResponse(
            status_code=202,
            content={
                "task_id": task_id,
                "workflow_id": workflow_id,
                "status": "queued",
                "message": "Task submitted for processing"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit task: {str(e)}"
        )

@app.post("/sagas")
@require_scope("saga:create")
async def create_saga(
    saga_request: dict,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """Create a multi-agent saga workflow."""
    
    saga_id = saga_request.get("saga_id") or f"saga-{dt.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
    saga_request["saga_id"] = saga_id
    saga_request["user_id"] = current_user.user_id
    
    try:
        workflow_id = await temporal_manager.execute_saga_workflow(saga_request)
        
        return JSONResponse(
            status_code=202,
            content={
                "saga_id": saga_id,
                "workflow_id": workflow_id,
                "status": "running",
                "message": "Saga workflow started"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start saga: {str(e)}"
        )

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


# Add CORS and security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# Authentication endpoints
@app.post("/auth/login", response_model=TokenResponse)
async def login(
    login_request: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Authenticate user and return JWT token."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "unknown")
    
    try:
        user, token = await user_service.authenticate_user(
            login_request, ip_address, user_agent
        )
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=24 * 3600,  # 24 hours
            user_id=str(user.id),
            username=user.username,
            roles=user.roles
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

@app.post("/auth/logout")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user by invalidating their session."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    # Invalidate current user session
    await user_service.invalidate_user_sessions(user.user_id)
    
    return {"message": "Logged out successfully"}

@app.post("/auth/change-password")
async def change_password(
    password_data: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    await user_service.change_password(user.user_id, password_data)
    return {"message": "Password changed successfully"}

@app.post("/auth/setup-mfa")
async def setup_mfa(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup MFA for current user."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    mfa_data = await user_service.setup_mfa(user.user_id)
    return mfa_data

@app.post("/auth/enable-mfa")
async def enable_mfa(
    token: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable MFA after verifying setup token."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    await user_service.enable_mfa(user.user_id, token)
    return {"message": "MFA enabled successfully"}

@app.post("/auth/disable-mfa")
async def disable_mfa(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable MFA for current user."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    await user_service.disable_mfa(user.user_id)
    return {"message": "MFA disabled successfully"}

# Secured endpoints
@app.get("/")
async def root() -> Dict[str, Any]:
    """Public health check - no auth required."""
    return {"status": "ok", "service": "api", "env": os.getenv("ENV", "dev")}

# User management endpoints
@app.post("/users", response_model=UserResponse)
@require_scope("users:write")
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Create a new user account."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    return await user_service.create_user(user_data, current_user.username)

@app.get("/users", response_model=list[UserResponse])
@require_scope("users:read")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[UserResponse]:
    """List all users with pagination."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    return await user_service.list_users(skip, limit)

@app.get("/users/{user_id}", response_model=UserResponse)
@require_scope("users:read")
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Get user by ID."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
@require_scope("users:write")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Update user information."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    return await user_service.update_user(user_id, user_data, current_user.username)

@app.delete("/users/{user_id}")
@require_scope("users:delete")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a user (deactivate)."""
    redis_client = await get_redis()
    user_service = UserService(db, redis_client)
    
    await user_service.delete_user(user_id, current_user.username)
    return {"message": "User deleted successfully"}

# Role management endpoints
@app.post("/roles", response_model=RoleResponse)
@require_scope("admin:write")
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RoleResponse:
    """Create a new role."""
    redis_client = await get_redis()
    role_service = RoleService(db, redis_client)
    
    return await role_service.create_role(
        role_data.name, role_data.description, role_data.permissions
    )

@app.get("/roles", response_model=list[RoleResponse])
@require_scope("users:read")
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[RoleResponse]:
    """List all roles."""
    redis_client = await get_redis()
    role_service = RoleService(db, redis_client)
    
    return await role_service.list_roles()

@app.get("/roles/{role_id}", response_model=RoleResponse)
@require_scope("users:read")
async def get_role(
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RoleResponse:
    """Get role by ID."""
    redis_client = await get_redis()
    role_service = RoleService(db, redis_client)
    
    role = await role_service.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return role

@app.put("/roles/{role_id}", response_model=RoleResponse)
@require_scope("admin:write")
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RoleResponse:
    """Update role information."""
    redis_client = await get_redis()
    role_service = RoleService(db, redis_client)
    
    return await role_service.update_role(
        role_id, role_data.description, role_data.permissions
    )

@app.delete("/roles/{role_id}")
@require_scope("admin:delete")
async def delete_role(
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a role."""
    redis_client = await get_redis()
    role_service = RoleService(db, redis_client)
    
    await role_service.delete_role(role_id)
    return {"message": "Role deleted successfully"}

@app.get("/healthz/deps")
@require_scope("system:health")
async def healthz_deps(user: User = Depends(get_current_user)) -> JSONResponse | Dict[str, Any]:
    """Deep healthcheck - requires system:health scope."""
    details, ok = await _check_dependencies()
    status = {"status": "ok" if ok else "degraded", "deps": details}
    if ok:
        return status
    return JSONResponse(status_code=503, content=status)

async def _get_message_handler() -> ProductionMessageHandler:
    """Get or create the production message handler."""
    global _message_handler
    if _message_handler is None:
        nc = await _get_nats()
        secret = os.getenv("TASK_SIGNING_SECRET", JWT_SECRET)
        producer_id = os.getenv("API_PRODUCER_ID", "maf-api")
        _message_handler = ProductionMessageHandler(nc, secret, producer_id)
    return _message_handler

@app.post("/tasks")
@require_scope("tasks:create")
async def submit_task(t: Task, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Submit task with production message handler and proper validation."""
    
    # Create TaskMessage with proper payload structure
    task_payload = TaskPayload(
        description=t.payload.get("description", ""),
        requirements=t.payload.get("requirements", []),
        context=t.payload.get("context", {}),
        metadata=t.payload.get("metadata", {})
    )
    
    task_message = TaskMessage(
        task_id=t.task_id,
        role=t.role,
        payload=task_payload,
        user_id=user.user_id,
        correlation_id=t.task_id
    )
    
    # Mark status queued in Redis with user context
    task_data = {
        "status": "queued",
        "role": t.role,
        "created_by": user.user_id,
        "created_at": dt.datetime.utcnow().isoformat(),
        "message_id": str(task_message.message_id)
    }
    await r.hset(f"task:{t.task_id}", mapping=task_data)
    await r.expire(f"task:{t.task_id}", TASK_TTL_SECONDS)
    
    # Publish using production message handler
    handler = await _get_message_handler()
    
    # Add tracing headers if available
    traceparent = t.payload.get("traceparent")
    
    nats_msg_id = await handler.publish_message(
        message=task_message,
        headers={"sender": user.user_id},
        traceparent=traceparent
    )
    
    return {
        "accepted": True,
        "task_id": t.task_id,
        "role": t.role,
        "subject": task_message.get_nats_subject(),
        "message_id": str(task_message.message_id),
        "nats_msg_id": nats_msg_id
    }

@app.get("/tasks/{task_id}/status")
@require_scope("tasks:read")
async def get_status(task_id: str, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get task status with access control."""
    data = await r.hgetall(f"task:{task_id}")
    if not data:
        raise HTTPException(status_code=404, detail="No status for this task")
    
    # Check if user can access this task
    if "admin" not in user.roles and data.get("created_by") != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"task_id": task_id, **data}

@app.get("/results/{task_id}")
@require_scope("results:read")
async def get_result(task_id: str, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get task result with access control."""
    async with await psycopg.AsyncConnection.connect(PG_URI) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT task_id, role, content, created_at FROM results WHERE task_id=%s",
                (task_id,),
            )
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Result not found")
            
            # Check task ownership for non-admin users
            if "admin" not in user.roles:
                task_data = await r.hgetall(f"task:{task_id}")
                if task_data.get("created_by") != user.user_id:
                    raise HTTPException(status_code=403, detail="Access denied")
            
            created_at = row[3]
            created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
            return {"task_id": row[0], "role": row[1], "content": row[2], "created_at": created_iso}

@app.get("/results")
@require_scope("results:read")
async def list_results(limit: int = 50, user: User = Depends(get_current_user)) -> list[Dict[str, Any]]:
    """List results with user-based filtering."""
    limit = max(1, min(500, limit))
    
    # Admin can see all results, others only their own
    if "admin" in user.roles:
        query = """
            SELECT r.task_id, r.role, LEFT(r.content, 160) AS preview, r.created_at
            FROM results r
            ORDER BY r.created_at DESC
            LIMIT %s
        """
        params = (limit,)
    else:
        # Join with Redis task data to filter by creator
        # This is simplified - in production, store creator in Postgres
        query = """
            SELECT task_id, role, LEFT(content, 160) AS preview, created_at
            FROM results
            ORDER BY created_at DESC
            LIMIT %s
        """
        params = (limit,)
    
    async with await psycopg.AsyncConnection.connect(PG_URI) as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            rows = await cur.fetchall()
            out: list[Dict[str, Any]] = []
            for rec in rows:
                created_at = rec[3]
                created_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
                out.append({"task_id": rec[0], "role": rec[1], "preview": rec[2], "created_at": created_iso})
            return out

@app.post("/ingest")
@require_scope("ingest:create")
async def ingest(item: IngestItem, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Ingest document with authentication."""
    try:
        doc_id = item.doc_id or f"doc_{dt.datetime.utcnow().isoformat()}"
        
        # Add user context to metadata
        metadata = item.metadata.copy()
        metadata.update({
            "created_by": user.user_id,
            "created_at": dt.datetime.utcnow().isoformat()
        })
        
        upsert_document(doc_id, item.text, metadata)
        return {"success": True, "doc_id": doc_id, "message": "Document ingested successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {e}")
