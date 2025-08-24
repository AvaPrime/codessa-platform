import asyncio
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

@dataclass
class TaskEnvelope:
    task_id: str
    idempotency_key: str
    attempt: int
    max_attempts: int
    created_at: str
    retry_after: Optional[str] = None
    payload: Dict[str, Any] = None

class NATSOrchestrator:
    """NATS-based orchestrator with retry and idempotency"""
    
    def __init__(self, nats_client, redis_client):
        self.nc = nats_client
        self.js = nats_client.jetstream()
        self.redis = redis_client
        
    async def submit_task_with_retry(self, task_id: str, role: str, payload: Dict[str, Any], retry_config: RetryConfig = None) -> str:
        """Submit task with built-in retry mechanism"""
        
        if not retry_config:
            retry_config = RetryConfig()
            
        # Generate idempotency key
        idempotency_key = f"{task_id}_{hash(json.dumps(payload, sort_keys=True))}"
        
        # Check if already processed
        existing = await self.redis.get(f"idempotency:{idempotency_key}")
        if existing:
            return json.loads(existing)["result"]
        
        # Create task envelope
        envelope = TaskEnvelope(
            task_id=task_id,
            idempotency_key=idempotency_key,
            attempt=1,
            max_attempts=retry_config.max_attempts,
            created_at=datetime.utcnow().isoformat(),
            payload=payload
        )
        
        # Publish to NATS with retry stream
        await self.js.publish(
            f"tasks.{role}",
            json.dumps(asdict(envelope)).encode(),
            headers={"Nats-Msg-Id": idempotency_key}  # NATS deduplication
        )
        
        # Store idempotency record
        await self.redis.setex(
            f"idempotency:{idempotency_key}",
            86400,  # 24h TTL
            json.dumps({"status": "submitted", "task_id": task_id})
        )
        
        return task_id
    
    async def handle_task_failure(self, envelope: TaskEnvelope, error: str) -> bool:
        """Handle task failure with retry logic"""
        
        if envelope.attempt >= envelope.max_attempts:
            # Send to DLQ
            await self.js.publish(
                f"dead_letter.{envelope.payload.get('role', 'unknown')}",
                json.dumps({
                    **asdict(envelope),
                    "final_error": error,
                    "failed_at": datetime.utcnow().isoformat()
                }).encode()
            )
            return False
        
        # Calculate retry delay with exponential backoff
        retry_config = RetryConfig()  # Could be passed in
        delay = min(
            retry_config.initial_delay * (retry_config.backoff_multiplier ** (envelope.attempt - 1)),
            retry_config.max_delay
        )
        
        # Add jitter
        if retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        # Schedule retry
        retry_envelope = TaskEnvelope(
            task_id=envelope.task_id,
            idempotency_key=envelope.idempotency_key,
            attempt=envelope.attempt + 1,
            max_attempts=envelope.max_attempts,
            created_at=envelope.created_at,
            retry_after=(datetime.utcnow() + timedelta(seconds=delay)).isoformat(),
            payload=envelope.payload
        )
        
        # Publish retry with delay (using NATS scheduled messages if available)
        await asyncio.sleep(delay)  # Simple delay, could use NATS scheduling
        await self.js.publish(
            f"tasks.{envelope.payload.get('role')}",
            json.dumps(asdict(retry_envelope)).encode()
        )
        
        return True