from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from .base_message import BaseMessage, MessageType
from enum import Enum
import uuid

class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class AgentRole(str, Enum):
    DOC_WRITER = "doc_writer"
    FRONTEND_DEV = "frontend_dev"
    BACKEND_DEV = "backend_dev"
    QA_TESTER = "qa_tester"
    COMPLIANCE_CHECKER = "compliance_checker"

class TaskPayload(BaseModel):
    """Task-specific business data"""
    
    # Core task data
    description: str = Field(..., min_length=1, max_length=10000)
    requirements: List[str] = Field(default_factory=list, max_length=50)
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Agent configuration (hints, not enforcement)
    agent_config: Dict[str, Any] = Field(default_factory=dict)
    model_profile: Optional[str] = Field(None, description="Model profile hint")
    
    # Resource hints (JetStream consumer config is source of truth)
    timeout_hint_seconds: Optional[int] = Field(None, ge=1, le=3600, description="Timeout hint for consumer")
    max_tokens_hint: Optional[int] = Field(None, ge=1, le=32000, description="Token limit hint")
    
    # Workflow dependencies
    depends_on: List[uuid.UUID] = Field(default_factory=list, description="Task UUIDs this depends on")
    workflow_id: Optional[uuid.UUID] = Field(None, description="Parent workflow UUID")
    
    @field_validator('depends_on')
    @classmethod
    def validate_dependencies(cls, v):
        if len(v) > 20:
            raise ValueError('Maximum 20 dependencies allowed')
        return v

class TaskMessage(BaseMessage):
    """Production task message - business data only"""
    
    message_type: Literal[MessageType.TASK] = MessageType.TASK
    schema_id: str = Field(default="task@1.0", const=True)
    
    # Task identification (UUIDs for better performance)
    task_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    
    # Agent assignment
    role: AgentRole = Field(..., description="Target agent role")
    agent_id: Optional[str] = Field(None, description="Specific agent instance")
    
    # Task business data
    payload: TaskPayload = Field(..., description="Task-specific data")
    
    # User context
    user_id: uuid.UUID = Field(..., description="User who submitted the task")
    
    # Status (for initial state)
    status: TaskStatus = Field(default=TaskStatus.QUEUED)
    
    @classmethod
    def get_schema_id(cls) -> str:
        return "task@1.0"
    
    def get_nats_subject(self) -> str:
        """Get NATS subject for this task (no task_id in subject)"""
        return f"tasks.{self.role}"