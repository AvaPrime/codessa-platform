# Message Contracts and Schema Guide

## Overview

This document defines the data contracts and schemas for the Multi-Agent Factory message queuing system, ensuring reliable and type-safe inter-service communication.

## Schema Hierarchy
BaseMessage (abstract)
├── TaskMessage
├── ResultMessage
├── StatusMessage
└── HeartbeatMessage

### BaseMessage
The base message class defines common fields and methods for all message types. It is an abstract class and cannot be instantiated directly.

### TaskMessage
The task message class represents a task to be performed by an agent. It contains fields for the task ID, role, payload, and other metadata.

### ResultMessage
The result message class represents the result of a task execution. It contains fields for the task ID, role, result type, result data, and other metadata.

### StatusMessage
The status message class represents the status of a task. It contains fields for the task ID, role, status, and other metadata.

### HeartbeatMessage
The heartbeat message class represents a heartbeat message sent by an agent to indicate that it is still alive. It contains fields for the agent ID, timestamp, and other metadata.


## Usage Examples

### Publishing a Task

```python
from config.schemas.task_message import TaskMessage, TaskPayload, AgentRole
from config.schemas.security import SignedEnvelope

# Create task payload
payload = TaskPayload(
    description="Generate API documentation",
    requirements=["Include examples", "Follow OpenAPI spec"],
    timeout_seconds=600
)

# Create task message
task = TaskMessage(
    task_id="task-123",
    idempotency_key="doc-gen-456",
    role=AgentRole.DOC_WRITER,
    payload=payload,
    user_id="user-789",
    correlation_id="req-abc",
    subject="tasks.doc_writer"
)

# Create signed envelope
envelope = SignedEnvelope.create_signed(
    message=task.dict(),
    subject="tasks.doc_writer",
    secret=os.getenv("TASK_SIGNING_SECRET")
)

# Publish to NATS
await js.publish("tasks.doc_writer", envelope.json().encode())
```

### Consuming and Validating Messages

```python
from config.schemas.validation import validator

async def message_handler(msg):
    # Validate envelope
    envelope_data = json.loads(msg.data.decode())
    result = validator.validate_envelope(envelope_data, secret)
    
    if not result.is_valid:
        logger.error(f"Invalid message: {result.errors}")
        await msg.nak()
        return
    
    # Process validated message
    task_data = result.validated_data['message']
    task = TaskMessage(**task_data)
    
    # Handle task...
    await process_task(task)
    await msg.ack()
```

## Schema Evolution

### Versioning Strategy

1. **Backward Compatible Changes**: Add optional fields, increase limits
2. **Breaking Changes**: Increment schema version, maintain compatibility period
3. **Deprecation**: Mark fields as deprecated, provide migration path

### Migration Process

1. Deploy new schema version alongside existing
2. Update producers to use new schema
3. Update consumers to handle both versions
4. Remove old schema after compatibility period

## Validation Rules

### Required Validations

- **Message Structure**: All required fields present and correctly typed
- **Business Logic**: Task dependencies, role assignments, resource limits
- **Security**: Signature verification, message age, sender authorization
- **Size Limits**: Message size within configured limits
- **Rate Limits**: Publisher rate limiting per user/tenant

### Error Handling

- **Validation Failures**: Send to dead letter queue with error details
- **Retry Logic**: Exponential backoff with jitter
- **Circuit Breaker**: Temporarily disable failing consumers
- **Monitoring**: Track validation failure rates and patterns

## Best Practices

1. **Always validate messages** before processing
2. **Use correlation IDs** for request tracing
3. **Set appropriate TTLs** to prevent message accumulation
4. **Monitor schema compliance** in production
5. **Test schema changes** thoroughly before deployment
6. **Document breaking changes** in release notes
7. **Use semantic versioning** for schema versions
