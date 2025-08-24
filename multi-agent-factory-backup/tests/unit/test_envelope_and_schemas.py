# File: tests/unit/test_envelope_and_schemas.py
# Purpose: Sanity tests for envelope verification and basic schema round-trip.

from __future__ import annotations
from config.schemas.messages import TaskMessage, TaskPayload
from config.schemas.envelope import SignedEnvelope
from config.schemas.validation import validate_envelope

def test_envelope_roundtrip_ok():
    msg = TaskMessage(
        schema="task@1.0",
        subject="tasks.doc_writer",
        role="doc_writer",
        message_type="task",
        task_id="t-1",
        user_id="u-1",
        payload=TaskPayload(description="Write docs"),
    )
    env = SignedEnvelope.sign(subject=msg.subject, message=msg.model_dump(), secret="s3cr3t")
    validated = validate_envelope(env.model_dump(), secret="s3cr3t")
    assert validated.task_id == "t-1"
    assert validated.role == "doc_writer"