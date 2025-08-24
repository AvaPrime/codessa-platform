# Architecture

## Components
- **API** (FastAPI): accepts tasks, tracks status, exposes health/metrics.
- **Agents** (NATS consumers): isolated workers per capability.
- **Orchestrator**: routes tasks to agents using `config/models.yaml`.
- **Memory** (Postgres + pgvector): document store + embeddings.
- **Messaging** (NATS JetStream): subjects per agent, DLQ for failures.
- **Infra**: Docker Compose for local; K8s manifests + Helm for prod.

## Data Flow (happy path)
1. Client → API `/tasks` (JWT).
2. API publishes to `tasks.<role>` (NATS).
3. Agent `<role>` consumes, does work, persists results.
4. API polls DB or subscribes to `results.<role>`, returns status.

## Reliability
- At-least-once delivery via JetStream.
- DLQ subjects: `dead_letter.<role>` with replay tooling.
- Health: `/livez`, `/readyz`, `/startupz` per service.
