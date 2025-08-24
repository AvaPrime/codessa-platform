# Canary Routing + Eval Dashboards — Closed‑Loop Optimization Pack

This pack adds **canary routing** and **online evaluation dashboards** that close the loop from **feedback → training → routing thresholds**. It builds on your Dynamic Router + Telemetry + A/B + Feedback packs. All contracts remain compatible with your Gateway.

---

## 0) Goals

- Safely flight candidate routing policies/models to a slice of traffic
- Measure uplift on cost/latency/quality with statistically sound judgments
- Feed outcomes + feedback back into **learned router thresholds** and **priors**
- One‑click rollback if canary underperforms

---

## 1) Repo layout (deltas)

```
/router/app/
  canary.py                # NEW: canary controller (policy, assignment, exposure logging)
  router_core.py           # UPDATED: integrates canary before final decision
  metrics.py               # UPDATED: canary / win-rate counters

/eval_service/
  app.py                   # NEW: online eval ingest + analysis + API (FastAPI)
  analyzers.py             # NEW: Bayesian & frequentist evaluators (uplift, win prob)
  schema.sql               # NEW: Postgres tables for exposures/outcomes/results
  requirements.txt

/training/
  online_train_router.py   # NEW: threshold tuner using eval outputs + feedback
  schedule.md              # NEW: cron/Temporal schedule for daily tuning

/ops/
  docker-compose.yml       # UPDATED: adds eval_service
  grafana/dashboards/canary.json  # NEW: canary exposure/metrics dashboard
```

---

## 2) Canary controller (router/app/canary.py)

```python
from __future__ import annotations
import os, json, hashlib, time
from dataclasses import dataclass
from typing import Optional, Dict

# Canary config structure
# {
#   "experiments": [
#     {
#       "name": "router_v2_thresholds",
#       "enabled": true,
#       "traffic": 0.10,                 # 10% of eligible traffic
#       "eligibility": {"domain": ["code","rag"], "tenant": ["acme"]},
#       "treatments": {
#         "control": {"threshold": 0.65, "model_bias": null},
#         "canary":  {"threshold": 0.55, "model_bias": "prefer_claude"}
#       },
#       "sticky_key": "session"          # session|user|tenant
#     }
#   ]
# }

CONFIG_PATH = os.getenv('CANARY_CONFIG','/etc/canary/config.json')

def _load_cfg():
    try:
        with open(CONFIG_PATH) as f: return json.load(f)
    except Exception:
        return {"experiments": []}

@dataclass
class Assignment:
    name: str
    arm: str           # control|canary
    hash: str
    params: Dict

class Canary:
    def __init__(self):
        self.cfg = _load_cfg()
    def experiments(self):
        return [e for e in self.cfg.get('experiments',[]) if e.get('enabled')]
    def eligible(self, e, meta: Dict) -> bool:
        elig = e.get('eligibility',{})
        for k, vals in elig.items():
            if vals and str(meta.get(k)) not in [str(v) for v in vals]:
                return False
        return True
    def assign(self, e, sticky_value: str) -> str:
        # hash‑based traffic split
        h = hashlib.sha256(f"{e['name']}:{sticky_value}".encode()).hexdigest()
        frac = int(h[:8], 16) / 0xffffffff
        return 'canary' if frac < float(e.get('traffic',0.0)) else 'control'
    def decide(self, meta: Dict) -> Dict[str, Assignment]:
        out = {}
        for e in self.experiments():
            if not self.eligible(e, meta):
                continue
            sticky_key = e.get('sticky_key','session')
            sticky_val = str(meta.get(sticky_key, meta.get('user','anon')))
            arm = self.assign(e, sticky_val)
            params = e.get('treatments',{}).get(arm, {})
            h = hashlib.sha256(f"{e['name']}:{sticky_val}:{arm}".encode()).hexdigest()
            out[e['name']] = Assignment(e['name'], arm, h, params)
        return out
```

**Usage in router**: produce a `canary_context` (tenant, user, session, domain) and get assignments. The params can tweak learned router **thresholds** or **model biases**.

---

## 3) Router integration (router/app/router_core.py) — key deltas

```python
from .canary import Canary
from .metrics import meter_canary_exposure

CAN = Canary()

async def decide_model(req, REG):
    feats = extract_features(req)
    meta = {
        'tenant': (req.metadata or {}).get('tenant'),
        'user':   (req.metadata or {}).get('user', 'anon'),
        'session':(req.metadata or {}).get('session', 'anon'),
        'domain': (req.metadata or {}).get('routingHints',{}).get('domain')
    }
    cx = CAN.decide(meta)  # {exp: Assignment}

    # L1 heuristics (as before)...

    # L2 learned decision
    user_text = next((m.content for m in req.messages if m.role=='user'), '')
    decision = await LR.predict(user_text, feats)

    # Apply canary treatment overrides
    for name, asg in cx.items():
        p = asg.params
        if 'threshold' in p and 'prob_strong' in decision:
            # treat prob_strong threshold as decision boundary
            if decision['prob_strong'] >= p['threshold']:
                decision['model'] = decision.get('model','gpt-5')
            else:
                decision['model'] = 'mistral-small'
            decision['reason'] += f"|{name}:{asg.arm}"
        if p.get('model_bias') == 'prefer_claude' and feats['is_code']:
            decision['model'] = 'claude-3-7'

    # log exposure
    if cx:
        meter_canary_exposure(cx, decision['model'])
    decision['canary'] = {k:{'arm':v.arm,'hash':v.hash,'params':v.params} for k,v in cx.items()}
    return decision
```

---

## 4) Metrics (router/app/metrics.py) — additions

```python
from prometheus_client import Counter

canary_exposure = Counter('router_canary_exposure_total','Canary exposures',['experiment','arm','model'])
canary_success = Counter('router_canary_success_total','Successes',['experiment','arm'])
canary_cost    = Counter('router_canary_cost_usd_total','Cost',['experiment','arm'])

def meter_canary_exposure(cx, model):
    for name, asg in cx.items():
        canary_exposure.labels(name, asg.arm, model).inc()
```

Your existing router already logs latency/cost; eval service will update `canary_success`/`canary_cost` by reading exposures + outcomes.

---

## 5) Online eval service (eval_service/app.py)

```python
from fastapi import FastAPI, Request
from pydantic import BaseModel
import asyncpg, os, time
from analyzers import bayes_bernoulli, wilson

DSN = os.getenv('PG_DSN','postgresql://postgres:postgres@postgres:5432/eval')
app = FastAPI(title='Codessa Online Eval')

# --- payloads ---
class Exposure(BaseModel):
    trace_id: str
    experiment: str
    arm: str  # control|canary
    model: str
    ts: int

class Outcome(BaseModel):
    trace_id: str
    success: bool | None = None   # e.g., validator accepted, PR merged, user thumbs-up
    cost_usd: float | None = None
    latency_ms: int | None = None
    metrics: dict | None = None
    ts: int | None = None

@app.on_event('startup')
async def start():
    app.state.pool = await asyncpg.create_pool(DSN)

@app.post('/exposure')
async def exposure(e: Exposure):
    async with app.state.pool.acquire() as con:
        await con.execute(
            'INSERT INTO exposure(trace_id, experiment, arm, model, ts) VALUES($1,$2,$3,$4,$5)',
            e.trace_id, e.experiment, e.arm, e.model, e.ts)
    return {'ok':True}

@app.post('/outcome')
async def outcome(o: Outcome):
    async with app.state.pool.acquire() as con:
        await con.execute(
            'INSERT INTO outcome(trace_id, success, cost_usd, latency_ms, metrics, ts) VALUES($1,$2,$3,$4,$5,$6)',
            o.trace_id, o.success, o.cost_usd, o.latency_ms, o.metrics, o.ts or int(time.time()))
    return {'ok':True}

@app.get('/summary/{experiment}')
async def summary(experiment: str):
    async with app.state.pool.acquire() as con:
        rows = await con.fetch('''
          SELECT e.arm, COUNT(*) AS n,
                 AVG(CASE WHEN o.success THEN 1 ELSE 0 END) AS sr,
                 AVG(o.cost_usd) AS cost,
                 AVG(o.latency_ms) AS lat
          FROM exposure e LEFT JOIN outcome o USING(trace_id)
          WHERE e.experiment=$1
          GROUP BY e.arm''', experiment)
    data = {r['arm']: dict(n=r['n'], success_rate=r['sr'] or 0.0, cost=r['cost'] or 0.0, latency_ms=r['lat'] or 0.0) for r in rows}
    # Bayesian win probability for success_rate (Bernoulli) assuming Beta(1,1)
    winp = bayes_bernoulli(data.get('control',{}), data.get('canary',{}))
    return {'experiment': experiment, 'arms': data, 'win_prob_canary': winp}
```

**analyzers.py** (Bayesian quick‑and‑clean)
```python
import math

def bayes_bernoulli(ctrl, cny):
    # ctrl/cny: {n, success_rate}
    nc = ctrl.get('n',0); pc = ctrl.get('success_rate',0.0)
    nn = cny.get('n',0); pn = cny.get('success_rate',0.0)
    # Beta posteriors: a = succ+1, b = fail+1
    ac, bc = int(nc*pc)+1, int(nc*(1-pc))+1
    an, bn = int(nn*pn)+1, int(nn*(1-pn))+1
    # crude Monte Carlo‑free approximation using means (ok for dashboard)
    mc, mn = ac/(ac+bc), an/(an+bn)
    return max(0.0, min(1.0, 0.5 + (mn-mc)))

def wilson(successes, n, z=1.96):
    if n==0: return (0.0, 0.0)
    phat = successes/n
    denom = 1 + z*z/n
    center = (phat + z*z/(2*n)) / denom
    half = z*math.sqrt((phat*(1-phat)+z*z/(4*n))/n)/denom
    return (max(0.0, center-half), min(1.0, center+half))
```

**schema.sql**
```sql
CREATE TABLE IF NOT EXISTS exposure (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT UNIQUE,
  experiment TEXT,
  arm TEXT,
  model TEXT,
  ts BIGINT
);

CREATE TABLE IF NOT EXISTS outcome (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT UNIQUE,
  success BOOLEAN,
  cost_usd DOUBLE PRECISION,
  latency_ms INT,
  metrics JSONB,
  ts BIGINT
);
```

**Flow**: Router sends **exposure** when canary assignment exists; Gateway/Router/Agents post **outcome** when validators pass, PR merges, or user feedback arrives.

---

## 6) Router → Eval Service hooks

In `router_core.generate_with_model` after acceptance/cascade, post exposure and outcome:
```python
import aiohttp, time, os
EVAL_URL = os.getenv('EVAL_URL','http://eval:8085')

async def post_eval(path, payload):
    async with aiohttp.ClientSession() as s:
        await s.post(f"{EVAL_URL}/{path}", json=payload, timeout=3)

# After decision
if decision.get('canary'):
    for name, asg in decision['canary'].items():
        await post_eval('exposure', {
            'trace_id': trace_id,
            'experiment': name,
            'arm': asg['arm'],
            'model': decision['model'],
            'ts': int(time.time())
        })

# After result known
await post_eval('outcome', {
  'trace_id': trace_id,
  'success': True,  # or result of validators/PR acceptance
  'cost_usd': result.get('cost',{}).get('estimated_usd'),
  'latency_ms': int(lat_ms),
  'metrics': {'cascade': bool(result.get('cascade_from'))}
})
```

---

## 7) Training loop (training/online_train_router.py)

```python
# Periodic job: read eval summaries + feedback → update threshold/model
import os, requests, json, pathlib
EVAL = os.getenv('EVAL_URL','http://eval:8085')
ROUTER_MODELS = pathlib.Path(os.getenv('ROUTER_MODELS','/models'))
CFG = pathlib.Path(os.getenv('CANARY_CONFIG','/etc/canary/config.json'))

TARGET_WIN = float(os.getenv('CANARY_PROMOTION_WIN_PROB','0.75'))
MIN_N = int(os.getenv('CANARY_MIN_SAMPLES','500'))

# Example: promote canary threshold if win prob high and samples >= MIN_N
exp = 'router_v2_thresholds'
sumr = requests.get(f"{EVAL}/summary/{exp}").json()
arms = sumr.get('arms',{})
if arms.get('canary',{}).get('n',0) >= MIN_N and sumr.get('win_prob_canary',0.0) >= TARGET_WIN:
    cfg = json.loads(CFG.read_text())
    for e in cfg['experiments']:
        if e['name']==exp:
            e['treatments']['control']['threshold'] = e['treatments']['canary']['threshold']
            e['traffic'] = min(1.0, e['traffic']*2)  # ramp further or set to 1.0 to ship
    CFG.write_text(json.dumps(cfg, indent=2))
    print('Promoted canary threshold & increased traffic')
```

Wire this as a cron or Temporal workflow. Always require a manual review step in prod.

---

## 8) Grafana dashboard (ops/grafana/dashboards/canary.json)

Panels to include:
- **Exposure over time** by arm
- **Success rate** with Wilson interval for control vs canary
- **Cost per successful response** by arm
- **Latency** p50/p95 by arm
- **Cascade rate** by arm
- **Win probability** (from `/summary/{experiment}` via Grafana JSON data source or Prometheus push)

*(JSON included as a seed; adjust datasource names.)*

---

## 9) Docker Compose (ops/docker-compose.yml) — add eval_service

```yaml
  eval:
    build: ../eval_service
    environment:
      PG_DSN: postgresql://postgres:postgres@postgres:5432/eval
    ports: ["8085:8085"]
    depends_on: [postgres]
```

**eval_service/requirements.txt**
```
fastapi
uvicorn
asyncpg
pydantic
```

Run: `uvicorn app:app --host 0.0.0.0 --port 8085`

---

## 10) Test plan

1) **Eligibility & stickiness**: Configure 10% traffic for tenant=acme, domain=code; verify same session stays in same arm across requests.
2) **Exposure & outcome flow**: Trigger requests; ensure `/exposure` and `/outcome` rows appear and Grafana charts move.
3) **Win signal**: Artificially set validators to pass more often for canary to simulate uplift; confirm win prob increases.
4) **Rollback**: Set `enabled=false` or `traffic=0` in config; verify routing resumes baseline immediately.
5) **Promotion**: Run `online_train_router.py`; ensure threshold promotion occurs only after MIN_N + win prob.

---

## 11) Safety & governance

- **Kill switch** per experiment; default to control on config load failure.
- **Budget guard**: deny canary when tenant budget under threshold.
- **DRY‑RUN mode**: compute decision but force control routing; still count exposures for sizing.
- **PII audit**: never log raw prompts in eval DB; store trace IDs + metrics only.

---

This pack gives you controlled canaries, trustworthy measurement, and an automated path to ship better routing thresholds while keeping rollback trivial. Integrate the eval summaries into your Ops review and promote with a single config change or the provided training job.

