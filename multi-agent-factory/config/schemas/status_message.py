from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal
from datetime import datetime, timezone
from .base_message import BaseMessage, MessageType
from .task_message import TaskStatus, AgentRole
from enum import Enum
import uuid

class StatusMessage(BaseMessage):
    """Task status update message"""
    
    message_type: Literal[MessageType.STATUS] = MessageType.STATUS
    schema_id: str = Field(default="status@1.0", const=True)
    
    # Task reference
    task_id: uuid.UUID = Field(..., description="Task UUID")
    
    # Status information
    status: TaskStatus = Field(..., description="Current task status")
    progress_percent: Optional[int] = Field(None, ge=0, le=100)
    status_message: Optional[str] = Field(None, max_length=500)
    
    # Agent context
    agent_id: str = Field(..., description="Agent reporting status")
    role: AgentRole = Field(..., description="Agent role")
    
    # Additional context
    details: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def get_schema_id(cls) -> str:
        return "status@1.0"
    
    def get_nats_subject(self) -> str:
        return f"status.{self.role}"

class AgentHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"

class HeartbeatMessage(BaseMessage):
    """Agent heartbeat message"""
    
    message_type: Literal[MessageType.HEARTBEAT] = MessageType.HEARTBEAT
    schema_id: str = Field(default="heartbeat@1.0", const=True)
    
    # Agent identification
    agent_id: str = Field(..., description="Agent instance ID")
    role: AgentRole = Field(..., description="Agent role")
    agent_version: str = Field(..., description="Agent version")
    
    # Health information
    health: AgentHealth = Field(..., description="Agent health status")
    uptime_seconds: int = Field(..., ge=0, description="Agent uptime")
    
    # Performance metrics
    tasks_processed: int = Field(default=0, ge=0)
    tasks_failed: int = Field(default=0, ge=0)
    avg_processing_time_ms: Optional[float] = Field(None, ge=0)
    
    # Resource usage
    memory_usage_mb: Optional[float] = Field(None, ge=0)
    cpu_usage_percent: Optional[float] = Field(None, ge=0, le=100)
    
    # Queue information
    pending_tasks: int = Field(default=0, ge=0)
    
    @classmethod
    def get_schema_id(cls) -> str:
        return "heartbeat@1.0"
    
    def get_nats_subject(self) -> str:
        return f"heartbeat.{self.role}"