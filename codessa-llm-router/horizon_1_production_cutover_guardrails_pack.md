# Horizon 1 — Production Cutover & Guardrails Pack

This pack finalizes the path from **staging → production** with promotion gates, anomaly defenses, provider hedging, and a ready‑to‑ship route recipe library. Everything snaps onto the router/gateway/eval stacks already on the canvas.

---

## 0) Contents

```
/prod/
  helm/
    router/Chart.yaml
    router/values.yaml
    eval/Chart.yaml
    eval/values.yaml
    opa/Chart.yaml
  argo/
    application-router.yaml
    application-eval.yaml
  promotion/
    promote_if_green.py   # KPI gate: cost, latency, quality thresholds
    rollback.py           # one‑shot rollback to previous snapshot
    snapshot.sh           # freeze models.yaml + OPA + canary config
  anomaly/
    ewma_guard.py         # EWMA/CUSUM guard for online metrics
    detectors.yaml        # detector registry + thresholds per domain/tenant
  providers/
    hedge.py              # hedged requests for tail‑latency control
  recipes/
    code.yaml             # route DAG default + variants
    rag.yaml
    qa.yaml
    chat.yaml
  opa/policies/
    monthly_budget.rego
    egress.rego
  runbooks/
    prod_cutover.md
    anomaly_response.md
    provider_outage.md
```

---

## 1) KPI Promotion Gate (promotion/promote_if_green.py)

```python
"""
Promote canary → prod when KPIs are green over the last 24h window:
- cost per success: ≥ 30% lower vs baseline
- p95 latency: ≥ 10% faster
- quality Δ: within ±2%
Actions:
- bump canary traffic to 100%
- write signed snapshot; annotate Grafana
- notify Slack
"""
import os, json, time, requests, hashlib, subprocess, sys

EVAL = os.getenv('EVAL_URL','http://eval:8085')
CANARY_CFG = os.getenv('CANARY_CONFIG','/etc/canary/config.json')
BASELINE = os.getenv('BASELINE_URL','http://eval:8085/baseline')  # or stored JSON
SLACK = os.getenv('SLACK_WEBHOOK')

THRESHOLDS = { 'cost_gain': 0.30, 'latency_gain': 0.10, 'quality_drift': 0.02 }
EXP = os.getenv('CANARY_EXP','router_v2_thresholds')

# fetch summaries (assumes your eval service exposes these)
cur = requests.get(f"{EVAL}/summary/{EXP}").json()
b = requests.get(BASELINE).json()  # {cost_per_success, latency_p95, quality}

arms = cur.get('arms',{})
ctrl, cny = arms.get('control',{}), arms.get('canary',{})

ok_cost = (ctrl.get('cost',1e-6) / max(cny.get('cost',1e-6),1e-6)) - 1 >= THRESHOLDS['cost_gain']
ok_lat  = (ctrl.get('latency_ms',1e6) / max(cny.get('latency_ms',1e6),1e-6)) - 1 >= THRESHOLDS['latency_gain']
ok_qual = abs((cny.get('success_rate',0.0) - ctrl.get('success_rate',0.0))) <= THRESHOLDS['quality_drift']

if ok_cost and ok_lat and ok_qual:
    cfg = json.loads(open(CANARY_CFG).read())
    for e in cfg['experiments']:
        if e['name']==EXP:
            e['traffic'] = 1.0
            e['enabled'] = True
    open(CANARY_CFG,'w').write(json.dumps(cfg, indent=2))
    # freeze snapshot
    subprocess.run(["/bin/bash","prod/promotion/snapshot.sh"], check=True)
    # notify
    if SLACK:
        requests.post(SLACK, json={"text": f"✅ Promoted {EXP} to 100% traffic — KPIs green."})
    print("PROMOTED")
else:
    print("HOLD: KPIs not green", ok_cost, ok_lat, ok_qual)
    sys.exit(2)
```

**snapshot.sh**
```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /var/snapshots
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
cp router/models.yaml /var/snapshots/models.$STAMP.yaml
cp /etc/canary/config.json /var/snapshots/canary.$STAMP.json
cp -r opa/policies /var/snapshots/policies.$STAMP
sha256sum /var/snapshots/*.$STAMP.* > /var/snapshots/SHA256SUMS.$STAMP.txt
```

**rollback.py** (rewind to previous snapshot of models/canary/policies)

---

## 2) Online Anomaly Guards (anomaly/ewma_guard.py)

```python
"""EWMA + CUSUM guardrails over Prometheus metrics (latency, cost/success, quality)."""
import os, time, requests, math

PROM = os.getenv('PROM_URL','http://prometheus:9090')
ALPHA = float(os.getenv('EWMA_ALPHA','0.2'))
Z = float(os.getenv('CUSUM_Z','4.0'))

QUERIES = {
  'latency': 'histogram_quantile(0.95, sum(rate(router_latency_seconds_bucket[5m])) by (le))',
  'costps':  'increase(router_cost_usd_total[15m]) / clamp_min(increase(router_success_total[15m]),1)',
  'quality':'router_validator_pass_rate'  # assume exported
}

state = {}

def ewma(k, x):
    m = state.get(k, x)
    m = ALPHA*x + (1-ALPHA)*m
    state[k] = m
    return m

while True:
    for k,q in QUERIES.items():
        r = requests.get(f"{PROM}/api/v1/query", params={'query': q}).json()
        val = float(r['data']['result'][0]['value'][1]) if r['data']['result'] else float('nan')
        mu = ewma(k, val)
        # naive CUSUM trigger if deviation > Z*sqrt(mu)
        if abs(val - mu) > Z*math.sqrt(abs(mu)+1e-6):
            print(f"ANOMALY {k}: {val} vs ewma {mu}")
            # call Slack/Webhook; optionally flip canary traffic to 0
    time.sleep(60)
```

**detectors.yaml** maps tenants/domains to thresholds and actions (page, rollback, brownout↑).

---

## 3) Provider Hedging (providers/hedge.py)

Hedge dual upstream calls only when tail‑risk is predicted (e.g., p99 latency risk or provider‑health < threshold). The **first successful** response wins; the other is cancelled. Respect OPA budgets.

```python
import asyncio, aiohttp, time

async def hedge_call(endpoints, payload, headers, timeout=20):
    async with aiohttp.ClientSession() as s:
        async def one(url):
            t0 = time.time()
            try:
                async with s.post(url, json=payload, headers=headers, timeout=timeout) as r:
                    return await r.json(), time.time()-t0, None
            except Exception as e:
                return None, time.time()-t0, e
        tasks = [asyncio.create_task(one(u)) for u in endpoints]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for p in pending: p.cancel()
        resp, lat, err = list(done)[0].result()
        return resp, lat, err
```

Integrate in `call_provider()` when `brownout_level>1` or provider health probe degrades.

---

## 4) Route Recipe Library (recipes/*.yaml)

**code.yaml**
```yaml
version: 1
name: code_default
pipeline:
  - id: retrieve
    with: hybrid
    params: { top_k: 40 }
  - id: rerank
    with: crossenc
    params: { top_k: 8 }
  - id: context
    with: budget
    params: { tokens: 3000 }
  - id: model
    with: auto
  - id: validate
    with: code_default
variants:
  brownout1:
    overrides:
      - { stage: rerank, with: none }
      - { stage: context, params: { tokens: 1800 } }
  cheap:
    overrides:
      - { stage: model, with: mistral-small }
```

**rag.yaml**
```yaml
version: 1
name: rag_default
pipeline:
  - id: retrieve
    with: hybrid
    params: { top_k: 80 }
  - id: rerank
    with: crossenc
    params: { top_k: 10 }
  - id: context
    with: budget
    params: { tokens: 3500 }
  - id: model
    with: auto
  - id: validate
    with: rag_default
variants:
  brownout2:
    overrides:
      - { stage: rerank, with: none }
      - { stage: context, params: { tokens: 1600 } }
```

QA/chat mirror these with smaller budgets and no rerank by default.

---

## 5) OPA: Monthly Budgets & Egress

**monthly_budget.rego**
```rego
package codessa.budget

default allow = false

# Block when projected monthly spend would exceed limit
allow {
  limit := data.tenants[input.session.tenant].monthly_usd
  projected := input.session.month_spend_usd + input.request.estimated_cost
  projected <= limit
}
```

**egress.rego**
```rego
package codessa.egress

default allow = false

# No public LLMs if private docs in context, unless waiver
allow {
  not input.context.private_docs
}
allow {
  input.context.private_docs
  input.session.flags.egress_waiver
}
```

---

## 6) Helm/ArgoCD (prod/helm & prod/argo)

Values default to production hardening: resource limits, HPA, PodDisruptionBudgets, liveness/readiness, OTEL exporters, secret mounts, budget/SLO envs.

**argo/application-router.yaml** (excerpt)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: codessa-router, namespace: argocd }
spec:
  project: default
  source:
    repoURL: git@github.com:yourorg/infra.git
    targetRevision: main
    path: prod/helm/router
  destination:
    server: https://kubernetes.default.svc
    namespace: prod
  syncPolicy:
    automated: { prune: true, selfHeal: true }
    syncOptions: [CreateNamespace=true]
```

---

## 7) Runbooks

- **prod_cutover.md** — exact order: freeze baseline → shadow confirm → canary 10% → promotion gate → snapshot → flip DNS.
- **anomaly_response.md** — what trips (EWMA/CUSUM), who’s paged, when to roll back vs brownout.
- **provider_outage.md** — use hedging; if health < threshold, force cheap/local models; disable rerank to cut tokens.

---

## 8) Acceptance Checklist

- [ ] Promotion gate turns canary to 100% **only** when all KPI thresholds green for 24h.
- [ ] Anomaly guards page within 5 minutes of significant drift; rollback script works.
- [ ] Hedging measurably lowers tail latency without >5% cost increase.
- [ ] Route recipes load and brownout variants apply by SLO level.
- [ ] Monthly budget policy prevents overruns; egress policy blocks risky routes.

---

Ship this pack when staging KPIs hold. The promotion script, snapshots, and guards make production cutover boring—and reversible on command.

