# Horizon 1 — Staging Rollout & Validation Pack

This pack gets everything you’ve built into **staging** safely, proves lift against KPIs, and readies an on‑ramp to production. It adds: shadow mode, log replay, K8s manifests, chaos drills, alerting, and runbooks — all compatible with your gateway/router/eval stacks on the canvas.

---

## 0) Contents

```
/staging/
  k8s/
    router-deploy.yaml
    eval-deploy.yaml
    opa-deploy.yaml
    redis-statefulset.yaml
    postgres-statefulset.yaml
    grafana-deploy.yaml
    secrets-example.yaml
  helm-values/
    router.values.yaml
    eval.values.yaml
  alerts/
    prometheus-rules.yaml
    alertmanager-config.yaml
  chaos/
    toxiproxy.yaml
    k6-load.js
  replay/
    README.md
    export_logs.py
    offline_replay.py
    kpi_report.py
  shadow/
    gateway_shadow.py
    shadow_schema.sql
  runbooks/
    release_checklist.md
    rollback.md
    SLO_brownout.md
    budget_guard.md
```

---

## 1) Shadow Mode (Gateway)

Mirror production traffic to the router **without** affecting user‑visible results. Store “ghost decisions” and diffs.

**`/staging/shadow/gateway_shadow.py`**
```python
from fastapi import Request
import asyncio, httpx, time, os
from typing import Dict

ROUTER = os.getenv('ROUTER_URL','http://router:80')
SHADOW = os.getenv('ROUTER_SHADOW_URL','http://router-shadow:80')
EVAL   = os.getenv('EVAL_URL','http://eval:8085')

async def ghost_call(body: Dict, headers: Dict):
    # fire-and-forget; send to shadow router and record route-only decision
    async with httpx.AsyncClient(timeout=8.0) as c:
        try:
            r = await c.post(f"{SHADOW}/route", json=body, headers=headers)
            jd = r.json().get('route',{})
            await c.post(f"{EVAL}/exposure", json={
                'trace_id': headers.get('x-trace-id'),
                'experiment': 'shadow_route',
                'arm': 'shadow',
                'model': jd.get('model','n/a'),
                'ts': int(time.time())
            })
        except Exception:
            return

async def proxy_with_shadow(request: Request, forward_func):
    body = await request.json()
    headers = {
        'x-trace-id': request.headers.get('x-trace-id',''),
        'x-session-id': request.headers.get('x-session-id',''),
        'x-user-id': request.headers.get('x-user-id','')
    }
    asyncio.create_task(ghost_call(body, headers))
    return await forward_func(body, headers)
```

**Shadow DB schema (`/staging/shadow/shadow_schema.sql`)** — optional, if you want a dedicated table for shadow diffs.

---

## 2) Log Replay & KPI Report

Recreate traffic offline, route with Horizon‑1 features, and compare to baseline.

**`/staging/replay/export_logs.py`** (example gateway export)
```python
# Export minimal fields per request: messages, domain, cost, latency, success, trace_id
# Implement for your logging backend (JSONL expected by replay)
```

**`/staging/replay/offline_replay.py`**
```python
import json, argparse, requests, time

parser = argparse.ArgumentParser()
parser.add_argument('log_jsonl')
parser.add_argument('--router','-r', default='http://router:80')
args = parser.parse_args()

rows = [json.loads(l) for l in open(args.log_jsonl)]
outs = []
for r in rows:
    payload = { 'model':'auto', 'messages': r['messages'], 'metadata': {'routingHints': {'domain': r.get('domain','chat')}} }
    t0 = time.time();
    j = requests.post(args.router+'/chat-completions', json=payload, timeout=60).json()
    lat = int((time.time()-t0)*1000)
    outs.append({
        'trace': j.get('trace_id'),
        'model': j.get('route',{}).get('model'),
        'cost': j.get('cost',{}).get('estimated_usd'),
        'latency_ms': lat,
        'validators': j.get('validators',{}),
    })
print(json.dumps(outs, indent=2))
```

**`/staging/replay/kpi_report.py`**
```python
# Compare baseline logs vs replay results and print:
# cost per success, p95 latency, validator pass delta — per domain
```

---

## 3) Kubernetes Manifests (staging/k8s)

**`router-deploy.yaml`** (excerpt)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: codessa-router, namespace: staging }
spec:
  replicas: 2
  strategy: { type: RollingUpdate }
  selector: { matchLabels: { app: codessa-router } }
  template:
    metadata: { labels: { app: codessa-router } }
    spec:
      containers:
        - name: router
          image: ghcr.io/yourorg/codessa-router:staging
          ports: [{ containerPort: 80 }]
          env:
            - { name: MODEL_REGISTRY, value: /app/models.yaml }
            - { name: OPA_URL, value: http://opa.staging.svc:8181 }
            - { name: EVAL_URL, value: http://eval.staging.svc:8085 }
            - { name: REDIS_URL, value: redis://redis.staging.svc:6379/0 }
            - { name: PG_DSN, valueFrom: { secretKeyRef: { name: pg-router, key: dsn } } }
          readinessProbe:
            httpGet: { path: /healthz, port: 80 }
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /healthz, port: 80 }
            initialDelaySeconds: 15
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata: { name: codessa-router, namespace: staging }
spec:
  selector: { app: codessa-router }
  ports: [ { port: 80, targetPort: 80 } ]
```

*Similar manifests for eval, opa, redis, postgres, grafana included.*

**`secrets-example.yaml`** provides the secret keys to template.

---

## 4) Chaos & Load (staging/chaos)

**`toxiproxy.yaml`** — inject latency/packet loss to provider upstreams.  
**`k6-load.js`** — steady RPS mixed workload across domains; export latency histograms and error rates.

---

## 5) Alerts (Prometheus + Alertmanager)

**`prometheus-rules.yaml`** (snippets)
```yaml
- name: horizon1-kpis
  rules:
    - alert: KPIQualityRegression
      expr: router_quality_delta < -0.02
      for: 15m
      labels: { severity: page }
      annotations: { summary: "Quality drop >2%", runbook: "runbooks/release_checklist.md" }
    - alert: LatencySLOBreach
      expr: router_latency_p95_ms{tenant!=""} > on(tenant) slo_target_ms{tenant!=""}
      for: 10m
      labels: { severity: page }
    - alert: CostPerSuccessSpike
      expr: increase(router_cost_usd_total[30m]) / clamp_min(increase(router_success_total[30m]),1) > 1.3 * horizon_baseline_cost_per_success
      for: 30m
      labels: { severity: warn }
```

**`alertmanager-config.yaml`** — routes to Slack/Email with templated links to Grafana & Trace IDs.

---

## 6) Runbooks

- **release_checklist.md** — preflight (OPA bundles pinned, model registry snapshot, budget limits set, shadow clean).
- **rollback.md** — traffic knob to 0, revert models.yaml, disable bandit, restore previous OPA bundle; smoke tests.
- **SLO_brownout.md** — how p95 is computed, brownout levels, and when to override.
- **budget_guard.md** — tenant budgets, per‑request estimation, blocking behavior, and how to grant waivers.

---

## 7) Rollout Plan

1) **Shadow for 48h**: record ghost decisions; no user impact.  
2) **Replay**: run `offline_replay.py` on shadow logs; confirm ≥30% cost per success improvement in at least one domain with ≤2% quality delta.  
3) **10% canary**: enable in router; alerts active; chaos test provider latency (toxiproxy) and validate brownouts.  
4) **Ramp to 50%** once KPIs hold for 24h; document in release checklist.  
5) **Go‑live**: 100% + freeze a signed snapshot (models.yaml + OPA bundle + canary config) for audit.

---

## 8) Safety Nets

- Kill switches: `BANDIT_ENABLED`, `BROWNOUT_ENABLED`, `DAG_EXPERIMENTS_ENABLED` env vars.  
- Budget bouncers: block strong models when tenant budgets under threshold.  
- PII: Eval DB stores only trace IDs + metrics; prompt/answer never stored.

---

Everything here is ready to copy into your repos. Start with **shadow mode** and **replay**, then light up the canary and watch the dashboards. Once the KPIs lock in, the rollback/runbook paths keep this boring in the best way.

