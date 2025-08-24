# File: config/schemas/validation.py
# Purpose: Centralized validation and schema registry (by schema id like 'task@1.0').

from __future__ import annotations
from pydantic import BaseModel
from typing import Dict, Any, Type, Union
from .messages import (
    BaseMessage,
    TaskMessage,
    ResultMessage,
    StatusMessage,
    HeartbeatMessage,
)

SCHEMAS: Dict[str, Type[BaseModel]] = {
    "task@1.0": TaskMessage,
    "result@1.0": ResultMessage,
    "status@1.0": StatusMessage,
    "heartbeat@1.0": HeartbeatMessage,
}

def validate_message(data: Union[str, Dict[str, Any]]) -> BaseMessage:
    if isinstance(data, str):
        import json
        data = json.loads(data)
    schema_id = data.get("schema")
    model = SCHEMAS.get(schema_id)
    if not model:
        raise ValueError(f"Unknown schema '{schema_id}'")
    return model(**data)

def validate_envelope(env: Dict[str, Any], secret: str) -> BaseMessage:
    from .envelope import SignedEnvelope
    envelope = SignedEnvelope(**env)
    if not envelope.verify(secret):
        raise ValueError("Envelope signature invalid")
    return validate_message(envelope.message)
