from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, timezone
from .base_message import BaseMessage, MessageType
from .task_message import TaskStatus, AgentRole
from enum import Enum
import uuid

class ResultType(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    TIMEOUT = "timeout"

class ExecutionMetrics(BaseModel):
    """Execution metrics for observability"""
    
    processing_time_ms: int = Field(..., ge=0)
    tokens_used: Optional[int] = Field(None, ge=0)
    model_calls: int = Field(default=0, ge=0)
    memory_peak_mb: Optional[float] = Field(None, ge=0)
    cpu_time_ms: Optional[int] = Field(None, ge=0)
    
    # Cost tracking
    estimated_cost_usd: Optional[float] = Field(None, ge=0)
    
    # Quality metrics
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)

class ResultPayload(BaseModel):
    """Result business data"""
    
    # Core result
    content: str = Field(..., description="Primary result content")
    content_type: str = Field(default="text/markdown")
    
    # Structured outputs
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[Dict[str, str]] = Field(default_factory=list)
    
    # Error information (if applicable)
    error_code: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    error_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Model information
    model_used: Optional[str] = Field(None)
    prompt_tokens: Optional[int] = Field(None, ge=0)
    completion_tokens: Optional[int] = Field(None, ge=0)
    
    @field_validator('attachments')
    @classmethod
    def validate_attachments(cls, v):
        for attachment in v:
            if not all(key in attachment for key in ['name', 'content_type']):
                raise ValueError('Each attachment must have name and content_type')
        return v

class ResultMessage(BaseMessage):
    """Production result message"""
    
    message_type: Literal[MessageType.RESULT] = MessageType.RESULT
    schema_id: str = Field(default="result@1.0", const=True)
    
    # Task reference
    task_id: uuid.UUID = Field(..., description="Original task UUID")
    
    # Agent information
    role: AgentRole = Field(..., description="Agent role that processed the task")
    agent_id: str = Field(..., description="Specific agent instance ID")
    agent_version: Optional[str] = Field(None, description="Agent version")
    
    # Result details
    result_type: ResultType = Field(..., description="Type of result")
    payload: ResultPayload = Field(..., description="Result business data")
    
    # Execution tracking
    status: TaskStatus = Field(..., description="Final task status")
    started_at: datetime = Field(..., description="When processing started")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: ExecutionMetrics = Field(..., description="Execution metrics")
    
    @field_validator('completed_at', 'started_at')
    @classmethod
    def validate_timezone_aware(cls, v):
        if v.tzinfo is None:
            raise ValueError('Datetime must be timezone-aware')
        return v
    
    @field_validator('completed_at')
    @classmethod
    def completed_after_started(cls, v, info):
        if 'started_at' in info.data and v < info.data['started_at']:
            raise ValueError('completed_at must be after started_at')
        return v
    
    @classmethod
    def get_schema_id(cls) -> str:
        return "result@1.0"
    
    def get_nats_subject(self) -> str:
        """Get NATS subject for this result (no task_id in subject)"""
        return f"results.{self.role}"