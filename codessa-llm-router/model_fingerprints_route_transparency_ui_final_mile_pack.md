# Model Fingerprints + Route Transparency UI — Final Mile Pack

This pack wires **canary/eval results → model fingerprints → router priors** and ships a **route transparency UI** in PyGPT (trace/model/cost/canary + feedback). It’s designed to slot into the stacks you already have on the canvas.

---

## 0) What’s inside

```
/eval_service/
  app.py                # + /model_stats endpoints (domain/model aggregates)
  schema.sql            # (unchanged) exposure/outcome tables already exist

/training/
  fingerprint_from_eval.py  # NEW: build fingerprints per model & domain from eval DB
  promote_priors.py         # NEW: write priors into models.yaml safely

/router/app/
  registry.py           # UPDATED: supports priors per-domain; hot-reload on SIGHUP
  router_core.py        # UPDATED: expected-utility routing using priors

/pygpt-ui/
  RouteBadge.tsx        # NEW: React UI badge showing route info + feedback hooks
  api.ts                # NEW: tiny client for /feedback
  styles.css            # NEW: minimal styles (or Tailwind classes if available)

/ops/
  grafana/dashboards/prior-health.json # NEW: dashboard for priors drift & outcome
```

---

## 1) Eval Service: model stats API

**`/eval_service/app.py`** (append)
```python
from fastapi import Query

@app.get('/model_stats')
async def model_stats(domain: str = Query(None)):
    # Summarize by model over last 14 days
    async with app.state.pool.acquire() as con:
        rows = await con.fetch('''
          SELECT e.model,
                 COUNT(*)                    AS n,
                 AVG(CASE WHEN o.success THEN 1 ELSE 0 END) AS success_rate,
                 AVG(o.cost_usd)            AS avg_cost,
                 AVG(o.latency_ms)          AS avg_latency,
                 SUM(CASE WHEN o.success THEN o.cost_usd ELSE 0 END)/NULLIF(SUM(CASE WHEN o.success THEN 1 ELSE 0 END),0) AS cost_per_success
          FROM exposure e LEFT JOIN outcome o USING(trace_id)
          WHERE e.ts > extract(epoch from now() - interval '14 days')
          GROUP BY e.model
        ''')
    out = []
    for r in rows:
        out.append(dict(model=r['model'], n=r['n'], success_rate=float(r['success_rate'] or 0.0),
                        avg_cost=float(r['avg_cost'] or 0.0), avg_latency=int(r['avg_latency'] or 0),
                        cost_per_success=float(r['cost_per_success'] or 0.0)))
    return {"domain": domain, "models": out}
```

> If you store domain on exposure, add it to the GROUP BY and filter. Otherwise, infer domain from routingHints in router when posting exposure (recommended).

---

## 2) Build fingerprints & priors

**`/training/fingerprint_from_eval.py`**
```python
"""
Pull model aggregates from eval_service and convert to normalized fingerprints & priors per domain.
Outputs JSON:
{
  "domain": "code|rag|qa|chat",
  "generated_at": "2025-08-23T00:00:00Z",
  "models": {
    "gpt-5": {"quality": 0.83, "latency": 0.62, "cost": 0.18, "eu_weight": 0.71},
    "mistral-small": {"quality": 0.61, "latency": 0.84, "cost": 0.95, "eu_weight": 0.52}
  }
}
"""
import os, json, time, requests, math

EVAL = os.getenv('EVAL_URL','http://eval:8085')
DOMAINS = (os.getenv('DOMAINS','code,rag,qa,chat').split(','))

out = {"generated_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), "domains": {}}

for d in DOMAINS:
    r = requests.get(f"{EVAL}/model_stats", params={'domain': d}, timeout=30)
    models = r.json().get('models', [])
    if not models:
        continue
    # Normalize: quality ↑, latency ↓, cost ↓
    q = [m['success_rate'] for m in models]
    c = [m['avg_cost'] for m in models]
    l = [m['avg_latency'] for m in models]
    def norm_up(v):
        lo, hi = min(v), max(v)
        return [(x - lo) / (hi - lo + 1e-9) for x in v]
    def norm_down(v):
        lo, hi = min(v), max(v)
        return [1 - (x - lo) / (hi - lo + 1e-9) for x in v]
    qn, cn, ln = norm_up(q), norm_down(c), norm_down(l)
    pri = {}
    for i, m in enumerate(models):
        # Expected utility weight (tunable): wq=0.6, wl=0.2, wc=0.2
        eu = 0.6*qn[i] + 0.2*ln[i] + 0.2*cn[i]
        pri[m['model']] = {
            "quality": round(qn[i], 3),
            "latency": round(ln[i], 3),
            "cost": round(cn[i], 3),
            "eu_weight": round(eu, 3),
            "n": int(m['n'])
        }
    out['domains'][d] = pri

print(json.dumps(out, indent=2))
```

**`/training/promote_priors.py`**
```python
"""Merge priors into router/models.yaml under `priors:` then signal the router to reload."""
import sys, json, yaml, os, signal
from pathlib import Path

models_yaml = Path(os.getenv('MODEL_REGISTRY','router/models.yaml'))
priors_json = Path(sys.argv[1])
router_pid   = int(os.getenv('ROUTER_PID','0'))

priors = json.loads(priors_json.read_text())
mod = yaml.safe_load(models_yaml.read_text())

# attach priors per domain
for m in mod.get('models', []):
    m.setdefault('priors', {})
    for dom, dpri in priors.get('domains', {}).items():
        if m['id'] in dpri:
            m['priors'][dom] = dpri[m['id']]

models_yaml.write_text(yaml.safe_dump(mod, sort_keys=False))
if router_pid:
    os.kill(router_pid, signal.SIGHUP)
print('Priors merged and router signaled')
```

> Schedule both scripts via cron or Temporal. Keep minimum sample thresholds before updating.

---

## 3) Router: priors-aware routing

**`/router/app/registry.py`** (delta)
```python
# models now support `priors: { domain: { eu_weight, quality, latency, cost, n } }`
import yaml, os, signal
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ModelInfo:
    id: str
    provider: str
    price_per_1k_prompt: float|None = None
    price_per_1k_completion: float|None = None
    max_tokens: int|None = None
    tags: list[str] = field(default_factory=list)
    priors: Dict[str, dict] = field(default_factory=dict)  # domain->metrics

class ModelRegistry:
    ...
    def prior(self, model_id:str, domain:str) -> dict:
        m = self.models[model_id]
        return m.priors.get(domain, m.priors.get('default', {}))
    def best_by_prior(self, domain:str, candidates:list[str]) -> str:
        scored = [(self.prior(m, domain).get('eu_weight', 0.0), m) for m in candidates]
        scored.sort(reverse=True)
        return scored[0][1] if scored else candidates[0]
```

**`/router/app/router_core.py`** (delta)
```python
# combine learned prob with priors for expected utility

def pick_with_priors(domain, decision, REG):
    # candidate pool: cheap vs strong (expand later)
    cand = ['mistral-small', 'gpt-5', 'claude-3-7']
    # base score from learned prob: map prob_strong to utility weight
    p = float(decision.get('prob_strong', 0.5))
    scores = {}
    for m in cand:
        prior = REG.prior(m, domain)
        eu = prior.get('eu_weight', 0.5)
        # if strong model and p is high, boost; if cheap and p low, boost
        bias = (p if m in ['gpt-5','claude-3-7'] else (1-p))
        scores[m] = 0.6*eu + 0.4*bias
    return max(scores, key=scores.get)

async def decide_model(req, REG):
    feats = extract_features(req)
    domain = (req.metadata or {}).get('routingHints',{}).get('domain','chat')
    # heuristics ... then learned
    user_text = next((m.content for m in req.messages if m.role=='user'), '')
    decision = await LR.predict(user_text, feats)
    decision['model'] = pick_with_priors(domain, decision, REG)
    return decision
```

---

## 4) PyGPT: Route transparency UI

**`/pygpt-ui/RouteBadge.tsx`** (React; Tailwind optional)
```tsx
import React from 'react';
import { sendFeedback } from './api';

export default function RouteBadge({ trace, route, cost, latency, canary, onRerunStrong }:{
  trace: string;
  route: { model: string; decision: string; reason?: string };
  cost?: number;
  latency?: number;
  canary?: { [k:string]: { arm: 'control'|'canary' } };
  onRerunStrong?: () => void;
}) {
  const arm = canary && Object.values(canary)[0]?.arm;
  return (
    <div className="flex items-center gap-3 rounded-xl border px-3 py-2 text-sm">
      <span className="font-semibold">{route.model}</span>
      <span className="opacity-70">{route.decision}</span>
      {arm && <span className={`px-2 py-0.5 rounded ${arm==='canary'?'bg-yellow-100':'bg-gray-100'}`}>{arm}</span>}
      {typeof cost === 'number' && <span>cost: ${cost.toFixed(5)}</span>}
      {typeof latency === 'number' && <span>{latency} ms</span>}
      <button className="ml-2 underline" onClick={() => navigator.clipboard.writeText(trace)}>copy trace</button>
      <button className="ml-2" onClick={() => sendFeedback(trace, +1)}>👍</button>
      <button className="ml-1" onClick={() => sendFeedback(trace, -1)}>👎</button>
      {onRerunStrong && <button className="ml-auto px-2 py-1 border rounded" onClick={onRerunStrong}>Re-run strong</button>}
    </div>
  );
}
```

**`/pygpt-ui/api.ts`**
```ts
export async function sendFeedback(trace: string, rating: number) {
  await fetch(`${process.env.CODESSA_URL}/feedback`, {
    method: 'POST', headers: { 'content-type':'application/json' },
    body: JSON.stringify({ trace_id: trace, rating })
  });
}
```

**Integration hint**: When rendering an assistant message, pass `trace`, `route`, `cost.estimated_usd`, `latency_ms`, and `route.canary` from the gateway response to `<RouteBadge/>`. Implement `onRerunStrong` by sending the same prompt with `model: 'gpt-5'` (or by setting a header `x-model-preference: strong`).

---

## 5) Grafana: Prior Health dashboard

Panels:
- **EU weight by model** over time per domain (from a JSON scrape of models.yaml or a custom exporter)
- **Success rate / cost / latency** per model (from eval_service aggregates)
- **Promotion events** (Annotations): threshold or priors changes

Seed JSON in `/ops/grafana/dashboards/prior-health.json` with Prometheus + JSON plugin targets.

---

## 6) Runbook

1) **Nightly**: `fingerprint_from_eval.py | tee /tmp/priors.json`  
2) **Promote**: `python promote_priors.py /tmp/priors.json` (signals router SIGHUP)  
3) **Spot-check**: Grafana Prior Health + Canary dashboards
4) **UI**: Confirm RouteBadge appears; submit feedback and verify it lands in `gateway.feedback`

---

## 7) Safety & rollback

- Keep a **shadow copy** of the previous models.yaml; rollback on any anomaly.  
- Require minimum `n` per model/domain before priors update (enforce in scripts).  
- RouteBadge feedback is optional; throttle client calls.

---

Everything here is additive: plug it in, and your router will learn from real traffic, surface its choices to users, and adapt its priors without losing the guardrails you’ve installed.

