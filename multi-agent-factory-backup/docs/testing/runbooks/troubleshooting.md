---
title: Troubleshooting Runbook — Multi-Agent Factory
owner: DevOps (Name • handle@domain)
version: 1.0
last_reviewed: 2025-08-13
next_review: 2025-10-01
status: operational
---

# Troubleshooting Runbook

## Quick Health Check
Run these commands to quickly verify the system health:

```bash
make verify           # tooling + compose sanity
make up               # start stack
make curl             # API health probe
make nats-health      # NATS /healthz
```
Common Faults
API returns 5xx / high latency
Check DB/Redis connectivity: make db-shell, make redis-cli ping

Inspect rates/errors in Grafana; review Jaeger traces for tail latencies

Verify queue backlogs (NATS JetStream metrics)

Agents not processing tasks
Validate NATS availability; ensure subjects/consumers exist

Inspect agent container logs: make tail S=<agent-service>

Confirm DLQ behavior; replay once root cause resolved

Database issues
pg_isready health; check connection pool exhaustion

Validate migrations; examine deadlocks (pg_stat_activity)

Redis anomalies
redis-cli info memory; ensure eviction policy matches expectations

Watch for timeouts indicating network or CPU pressure

Message bus (NATS)
/healthz and /varz; confirm JetStream storage thresholds

Purge/compact if necessary; validate max payload constraints

Escalation
Critical path down ⇒ open incident, page on-call, roll back last change if correlated.
