# File: config/schemas/messages.py
# Purpose: Canonical Pydantic (v2) data contracts for NATS inter-service messages.

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, Optional, List, Literal
from uuid import UUID, uuid4
from datetime import datetime, timezone

# ---- Core literals/enums ----
MessageType = Literal["task", "result", "status", "heartbeat", "error"]
Priority    = Literal["low", "normal", "high", "critical"]
TaskStatus  = Literal["queued", "processing", "completed", "failed", "cancelled", "timeout"]
Role        = Literal["doc_writer", "frontend_dev", "backend_dev", "qa_tester", "compliance_checker"]
ResultType  = Literal["success", "partial", "error", "timeout"]

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

# ---- Base message ----
class BaseMessage(BaseModel):
    schema: str = Field(..., description="Schema id, e.g. 'task@1.0'")
    message_id: UUID = Field(default_factory=uuid4, description="Unique message GUID (used for dedup)")
    correlation_id: Optional[str] = Field(None, description="Logical correlation for tracing/search")
    message_type: MessageType
    subject: str = Field(..., description="NATS subject used for routing")
    reply_to: Optional[str] = Field(None, description="Optional subject for direct replies")
    timestamp: datetime = Field(default_factory=utcnow)
    priority: Priority = "normal"
    metadata: Dict[str, Any] = Field(default_factory=dict)

# ---- Task ----
class TaskPayload(BaseModel):
    description: str = Field(..., min_length=1, max_length=10_000)
    requirements: List[str] = Field(default_factory=list, description="Limit 50 items")
    context: Dict[str, Any] = Field(default_factory=dict)
    agent_config: Dict[str, Any] = Field(default_factory=dict)
    model_profile: Optional[str] = None
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    max_tokens: Optional[int] = Field(None, ge=1, le=32_000)
    depends_on: List[str] = Field(default_factory=list)
    workflow_id: Optional[str] = None

    @field_validator("requirements")
    @classmethod
    def _limit_requirements(cls, v: List[str]) -> List[str]:
        if len(v) > 50:
            raise ValueError("Maximum 50 requirements allowed")
        return v

class TaskMessage(BaseMessage):
    message_type: Literal["task"] = "task"
    task_id: str
    role: Role
    user_id: str
    tenant_id: Optional[str] = None
    status: TaskStatus = "queued"
    created_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    payload: TaskPayload

    @field_validator("subject")
    @classmethod
    def _subject_matches_role(cls, v: str, info):
        role = info.data.get("role")
        if role:
            expected = f"tasks.{role}"
            if v != expected:
                raise ValueError(f"subject must be '{expected}' for role '{role}'")
        return v

# ---- Result ----
class ExecutionMetrics(BaseModel):
    processing_time_ms: int = Field(..., ge=0)
    tokens_used: Optional[int] = Field(None, ge=0)
    model_calls: int = Field(default=0, ge=0)
    memory_peak_mb: Optional[float] = Field(None, ge=0)
    cpu_time_ms: Optional[int] = Field(None, ge=0)

class AttachmentRef(BaseModel):
    name: str
    content_type: str
    uri: Optional[str] = None           # Prefer external URIs over embedding bytes
    sha256: Optional[str] = None        # Integrity check for retrieved artifact

class ResultPayload(BaseModel):
    content: str
    content_type: str = "text/markdown"
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[AttachmentRef] = Field(default_factory=list)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_metrics: Dict[str, float] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = Field(default_factory=dict)
    model_used: Optional[str] = None
    prompt_tokens: Optional[int] = Field(None, ge=0)
    completion_tokens: Optional[int] = Field(None, ge=0)

class ResultMessage(BaseMessage):
    message_type: Literal["result"] = "result"
    task_id: str
    role: Role
    agent_id: str
    agent_version: Optional[str] = None
    result_type: ResultType
    payload: ResultPayload
    status: TaskStatus
    started_at: datetime
    completed_at: datetime = Field(default_factory=utcnow)
    metrics: ExecutionMetrics

    @field_validator("completed_at")
    @classmethod
    def _completed_after_started(cls, v: datetime, info):
        started = info.data.get("started_at")
        if started and v < started:
            raise ValueError("completed_at must be after started_at")
        return v

# ---- Status & Heartbeat ----
class StatusMessage(BaseMessage):
    message_type: Literal["status"] = "status"
    task_id: str
    role: Role
    status: TaskStatus
    detail: Optional[str] = None
    progress_pct: Optional[float] = Field(None, ge=0.0, le=100.0)

class HeartbeatMessage(BaseMessage):
    message_type: Literal["heartbeat"] = "heartbeat"
    agent_id: str
    role: Role
    agent_version: Optional[str] = None
    healthy: bool = True
