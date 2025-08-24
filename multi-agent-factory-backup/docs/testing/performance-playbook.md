<!-- File: docs/testing/runbooks/performance-playbook.md -->
---
title: Performance Playbook — Multi-Agent Factory
owner: Performance Eng (Name • handle@domain)
version: 1.0
last_reviewed: 2025-08-13
next_review: 2025-10-01
status: operational
---

# Performance Playbook

## SLOs & Budgets
- API p95 < 200 ms, error rate < 0.1%, throughput > 1000 tasks/min (nominal profile).
- Breach policy: create incident; scale out replicas; open perf-regression issue with flamegraphs and top offenders.

## Tooling
- **Load:** Locust (distributed optional)  
- **Metrics/Traces:** Prometheus + OTEL + Jaeger  
- **Dashboards:** Grafana “API Latency”, “Queue Depth”, “Agent Throughput”

## Procedure
1. **Bring up stack:** `make up` (or staging namespace in K8s).  
2. **Seed data:** scripts in `tests/performance/seeds/`.  
3. **Run load:**  
   ```bash
   locust -f tests/performance/locustfile.py --headless -u 200 -r 20 -t 10m --host http://localhost:8000
   ```
4. **Monitor:** Check Grafana dashboards; watch for SLO breaches.  
5. **Tear down:** `make down` (or delete namespace).

6. **Record:** export Prometheus snapshots; save Locust HTML/CSV to artifacts/perf/YYYY-MM-DD/.

7. **Analyze:** verify budgets; inspect Jaeger traces for tail latency; correlate with CPU/memory and NATS subject backlogs.

8. **Report:** file summary in artifacts/perf/.../report.md with hypotheses and actions.

**Stress & Breakpoint**
Step-up users (e.g., 50→100→200→500) until SLA violation; capture system behavior and recovery time after load shed.

**Capacity Planning**
Derive per-service QPS limits from CPU saturation curves; propose replica counts and HPA thresholds.
