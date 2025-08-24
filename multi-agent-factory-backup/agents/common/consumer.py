# File: agents/common/consumer.py
# Purpose: Example JetStream consumer loop with signature + schema validation.

from __future__ import annotations
import os, json, asyncio
from nats.aio.client import Client as NATS
from config.schemas.validation import validate_envelope

async def run_agent(nc: NATS, role: str, handler):
    js = nc.jetstream()
    sub = await js.subscribe(f"tasks.{role}", durable=f"{role}_durable")

    secret = os.getenv("TASK_SIGNING_SECRET", "dev-secret")

    async for msg in sub.messages:
        try:
            envelope = json.loads(msg.data.decode())
            inner = validate_envelope(envelope, secret=secret)
            await handler(inner)
            await msg.ack()
        except Exception:
            await msg.nak()  # redelivery up to max_deliver; DLQ routed by consumer policy

# Example handler signature:
# async def handler(task_message: TaskMessage): ...
