# Operations Runbook

## On-call Playbook
- **DLQ growth**: run `scripts/dlq_replay.py --from dead_letter.backend_dev` after fix.
- **Postgres migrations**: `alembic upgrade head` during deploy; rollback with `alembic downgrade -1`.
- **NATS outage**: agents retry with backoff; see alert `nats_connect_errors_total`.

## SLOs
- API p95 latency < 300ms
- Task success rate > 99%
- MTTR from DLQ < 5 minutes
