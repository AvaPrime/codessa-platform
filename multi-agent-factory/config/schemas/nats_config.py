from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from enum import Enum

class RetentionPolicy(str, Enum):
    LIMITS = "limits"
    INTEREST = "interest"
    WORKQUEUE = "workqueue"

class AckPolicy(str, Enum):
    NONE = "none"
    ALL = "all"
    EXPLICIT = "explicit"

class DeliverPolicy(str, Enum):
    ALL = "all"
    LAST = "last"
    NEW = "new"
    BY_START_SEQUENCE = "by_start_sequence"
    BY_START_TIME = "by_start_time"

class StreamConfig(BaseModel):
    """JetStream stream configuration"""
    
    name: str = Field(..., description="Stream name")
    subjects: List[str] = Field(..., description="Subject patterns")
    
    # Retention (source of truth for message lifecycle)
    retention: RetentionPolicy = Field(default=RetentionPolicy.LIMITS)
    max_consumers: int = Field(default=100, ge=1)
    max_msgs: int = Field(default=1000000, ge=1)
    max_bytes: int = Field(default=1073741824, ge=1)  # 1GB
    max_age: int = Field(default=604800, ge=1)  # 7 days
    max_msg_size: int = Field(default=8388608, ge=1)  # 8MB
    
    # Deduplication (uses Nats-Msg-Id header)
    duplicate_window: int = Field(default=120, ge=0)  # 2 minutes
    
    # Storage
    storage: str = Field(default="file", regex="^(file|memory)$")
    replicas: int = Field(default=1, ge=1, le=5)
    
    @field_validator('subjects')
    @classmethod
    def validate_subjects(cls, v):
        if not v:
            raise ValueError('At least one subject pattern required')
        # Validate subject cardinality
        for subject in v:
            if subject.count('.') > 3:  # Prevent subject explosion
                raise ValueError(f'Subject {subject} has too many tokens (max 4)')
        return v

class ConsumerConfig(BaseModel):
    """JetStream consumer configuration (source of truth for delivery)"""
    
    name: str = Field(..., description="Consumer name")
    stream_name: str = Field(..., description="Source stream")
    
    # Delivery (JetStream controls this, not payload hints)
    deliver_policy: DeliverPolicy = Field(default=DeliverPolicy.ALL)
    deliver_subject: Optional[str] = Field(None, description="Push consumer subject")
    durable_name: Optional[str] = Field(None, description="Durable consumer name")
    
    # Acknowledgment (source of truth for retries)
    ack_policy: AckPolicy = Field(default=AckPolicy.EXPLICIT)
    ack_wait: int = Field(default=30, ge=1)  # seconds - this is the real timeout
    max_deliver: int = Field(default=3, ge=1)  # this is the real max_attempts
    
    # Backoff (exponential backoff for retries)
    backoff: List[int] = Field(default_factory=lambda: [1, 5, 15], description="Backoff delays in seconds")
    
    # Flow control
    max_ack_pending: int = Field(default=1000, ge=1)
    max_waiting: int = Field(default=512, ge=1)
    
    # Filtering
    filter_subject: Optional[str] = Field(None, description="Subject filter")
    
    @field_validator('backoff')
    @classmethod
    def validate_backoff(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 backoff intervals')
        if any(delay < 0 for delay in v):
            raise ValueError('Backoff delays must be non-negative')
        return v

class NATSConfiguration(BaseModel):
    """Production NATS configuration"""
    
    # Connection
    url: str = Field(default="nats://nats:4222")
    max_reconnect_attempts: int = Field(default=5, ge=0)
    reconnect_time_wait: float = Field(default=1.0, ge=0.1)
    
    # JetStream
    enable_jetstream: bool = Field(default=True)
    streams: List[StreamConfig] = Field(default_factory=list)
    consumers: List[ConsumerConfig] = Field(default_factory=list)
    
    # Security
    tls_enabled: bool = Field(default=False)
    credentials_file: Optional[str] = Field(None)
    
    def get_production_streams(self) -> List[StreamConfig]:
        """Production stream configurations with proper subject cardinality"""
        return [
            StreamConfig(
                name="TASKS",
                subjects=["tasks.*"],  # tasks.{role} - no task_id in subject
                retention=RetentionPolicy.WORKQUEUE,
                max_msgs=100000,
                max_age=86400,  # 1 day
                duplicate_window=300  # 5 minutes for task dedup
            ),
            StreamConfig(
                name="RESULTS",
                subjects=["results.*"],  # results.{role} - no task_id in subject
                retention=RetentionPolicy.LIMITS,
                max_msgs=1000000,
                max_age=604800,  # 7 days
                duplicate_window=60  # 1 minute for result dedup
            ),
            StreamConfig(
                name="STATUS",
                subjects=["status.*"],  # status.{role}
                retention=RetentionPolicy.LIMITS,
                max_msgs=500000,
                max_age=86400,  # 1 day
                duplicate_window=30  # 30 seconds for status dedup
            ),
            StreamConfig(
                name="HEARTBEAT",
                subjects=["heartbeat.*"],  # heartbeat.{role}
                retention=RetentionPolicy.LIMITS,
                max_msgs=100000,
                max_age=3600,  # 1 hour
                duplicate_window=10  # 10 seconds for heartbeat dedup
            ),
            StreamConfig(
                name="DEAD_LETTERS",
                subjects=["dead_letter.*"],
                retention=RetentionPolicy.LIMITS,
                max_msgs=50000,
                max_age=2592000  # 30 days
            )
        ]