from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, Any, Optional, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid
import json

class MessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    STATUS = "status"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class BaseMessage(BaseModel):
    """Base message schema - transport concerns in headers, business data in payload"""
    
    # Schema identification
    schema_id: str = Field(..., description="Schema identifier like 'task@1.0'")
    
    # Core message data (business payload only)
    message_type: MessageType = Field(..., description="Type of message")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Human-friendly correlation ID")
    
    # Timing (timezone-aware)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Business metadata only (transport metadata goes in NATS headers)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        if v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware')
        return v
    
    @classmethod
    def get_schema_id(cls) -> str:
        """Override in subclasses to provide schema ID"""
        return "base@1.0"
    
    def model_dump_canonical(self) -> str:
        """Canonical JSON for signing (sorted keys, no whitespace)"""
        return json.dumps(self.model_dump(), sort_keys=True, separators=(',', ':'))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: str
        }

class NATSHeaders(BaseModel):
    """NATS message headers schema"""
    
    # JetStream deduplication (required)
    nats_msg_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="Nats-Msg-Id")
    
    # Schema evolution
    schema_id: str = Field(..., alias="Schema-Id")
    schema_version: str = Field(default="1.0", alias="Schema-Version")
    
    # W3C Trace Context for observability
    traceparent: Optional[str] = Field(None, alias="traceparent")
    tracestate: Optional[str] = Field(None, alias="tracestate")
    
    # Message routing and delivery
    reply_to: Optional[str] = Field(None, alias="Reply-To")
    priority: Priority = Field(default=Priority.NORMAL, alias="Priority")
    
    # Security
    signature: Optional[str] = Field(None, alias="Signature")
    key_id: Optional[str] = Field(None, alias="Key-Id")
    
    # Operational metadata
    producer_id: Optional[str] = Field(None, alias="Producer-Id")
    tenant_id: Optional[str] = Field(None, alias="Tenant-Id")
    
    class Config:
        populate_by_name = True  # Allow both field names and aliases