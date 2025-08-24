# File: orchestrator/publish.py
# Purpose: Example publisher that signs envelopes, sets headers (schema, trace), and leverages JetStream dedup.

from __future__ import annotations
import os, json
from nats.aio.client import Client as NATS
from config.schemas.messages import TaskMessage
from config.schemas.envelope import SignedEnvelope

async def publish_task(nc: NATS, task: TaskMessage) -> None:
    js = nc.jetstream()
    secret = os.getenv("TASK_SIGNING_SECRET", "dev-secret")
    subject = task.subject  # expected to be tasks.<role>

    envelope = SignedEnvelope.sign(
        subject=subject,
        message=task.model_dump(),
        secret=secret,
        nats_headers={
            "schema": task.schema,                           # e.g., task@1.0
            "traceparent": task.metadata.get("traceparent", ""),
            "tracestate": task.metadata.get("tracestate", ""),
        },
    )

    headers = envelope.nats_headers.copy()
    headers["Nats-Msg-Id"] = str(task.message_id)          # JetStream dedup id

    await js.publish(
        subject=subject,
        payload=envelope.model_dump_json().encode(),
        headers=headers,
    )
