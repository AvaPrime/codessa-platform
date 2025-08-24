<!-- File: docs/MESSAGE_CONTRACTS.md -->
# Message Contracts & Envelope — Multi-Agent Factory

This document is the human-readable companion to the Pydantic contracts under `config/schemas/`.

## Subjects
- **tasks.\<role\>** — work-queue semantics (JetStream `TASKS` stream)
- **results.\<role\>** — durable results (JetStream `RESULTS` stream)
- **dead_letter.>** — failures routed by consumer policy

Avoid per-task subjects (cardinality blow-up). Use `reply_to` for direct replies if needed.

## Required headers
- `schema`: e.g., `task@1.0`
- `Nats-Msg-Id`: set to the message UUID for deduplication
- `traceparent` (optional), `tracestate` (optional) for W3C tracing

## Envelope
Messages are signed with an HMAC envelope (`SignedEnvelope`). The envelope carries:
- `subject`, `message` (canonical JSON), `message_hash`, `signature`, `created_at`, `key_id`, and pass-through `nats_headers`.

Consumers must verify the envelope before parsing the inner message.

## Versioning
Increment the schema suffix (e.g., `task@1.1`) for breaking changes. Keep both versions registered during migration.

## Validation
- Publisher: construct the message (`TaskMessage` et al.), sign envelope, publish.
- Consumer: verify envelope → validate message → process → ack/nak.
