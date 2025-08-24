# Horizon 1 Pack — Per‑Domain Routers, Bandit Canaries, Route DAGs, SLO‑Aware Cascades

This pack delivers the four tracks for “ruthless practicality,” wired into your existing Codessa router/gateway/eval stack. Contracts remain stable.

---

## 0) Contents & Layout

```
/router/app/
  domains/
    __init__.py
    code.py          # features + validators for code
    rag.py           # features + validators for RAG
    qa.py            # features + validators for QA
    chat.py          # features + validators for chat
  bandit.py         # contextual Thompson Sampling (per-domain)
  dag.py            # route pipeline engine (retriever → reranker → ctx → model → validators)
  slo.py            # SLO monitor + brownout controller (per-tenant p95)
  router_core.py    # UPDATED: domain routers + bandit + DAG + SLO hooks
  metrics.py        # UPDATED: KPIs (cost/success, p95 latency, quality deltas)

/eval_service/
  analyzers.py      # UPDATED: reward R = α·success − β·cost − γ·latency
  app.py            # UPDATED: /reward, /domain_stats endpoints

/ops/grafana/dashboards/
  horizon1-kpis.json   # KPIs dashboard: cost per success, p95 latency, quality delta
  bandit.json          # exploration/exploitation, regret, arm share
  slo.json             # tenant SLO conformance, brownout rate

/docs/
  ROUTE_DAG_SPEC.md    # Declarative route recipe format
  SLO_README.md        # How SLO windows and brownouts work
```

---

## 1) Per‑Domain Routers

**`/router/app/domains/code.py`** (features + validators)
```python
import re, ast

def features(text: str) -> dict:
    t = text.lower()
    return {
        'len': len(text),
        'has_diff': ('+++ b/' in text) or ('--- a/' in text),
        'has_stacktrace': ('traceback' in t) or ('exception' in t),
        'lang_hint': 'py' if 'def ' in t or 'import ' in t else 'generic',
    }

def validators(answer: str) -> list[tuple[str,bool,str|None]]:
    ok_block = '```' in answer
    reason = None if ok_block else 'no_code_block'
    out = [('code_block', ok_block, reason)]
    # Best effort Python parse
    if ok_block and ('```' in answer):
        m = re.search(r"```(py|python)?\n(.*?)```", answer, re.S)
        if m:
            code = m.group(2)
            try:
                ast.parse(code)
                out.append(('py_syntax', True, None))
            except SyntaxError:
                out.append(('py_syntax', False, 'syntax_error'))
    return out
```

**`/router/app/domains/rag.py`**
```python
import re
CITE_RX = re.compile(r"\b(kb://|\[[0-9]+\])")

def features(text: str) -> dict:
    return { 'len': len(text), 'qmarks': text.count('?'), 'nums': sum(c.isdigit() for c in text) }

def validators(answer: str) -> list[tuple[str,bool,str|None]]:
    has_cite = bool(CITE_RX.search(answer))
    return [('citations', has_cite, None if has_cite else 'no_citations')]
```

**`/router/app/domains/qa.py`** and **`chat.py`** mirror with lightweight signals (question marks, entity density, toxicity check optional).

**Domain selection** (in `router_core.decide_model`): use `routingHints.domain` or fallback heuristics (presence of code markers, URLs/citations, etc.).

---

## 2) Bandit Canaries (Contextual Thompson Sampling)

**Goal:** replace fixed thresholds with a contextual bandit optimizing
`R = α·success − β·cost − γ·latency` per domain. Rewards are learned from eval_service and live traffic. Hard caps enforced via OPA.

**`/router/app/bandit.py`**
```python
from __future__ import annotations
import math, os, json, time, random
from dataclasses import dataclass
from typing import Dict, List

# Two-arm bandit (control vs canary) with linear Thompson Sampling per domain.
# Context φ(x) is a small feature vector (length, is_code, etc.).

@dataclass
class Arm:
    name: str  # 'control' or 'canary'
    theta: list[float]      # posterior mean
    A: list[list[float]]    # precision matrix (d x d)
    b: list[float]          # data vector (d)

class CTS:
    def __init__(self, dim: int, alpha=1.0):
        self.dim = dim
        self.alpha = alpha
        I = [[0.0]*dim for _ in range(dim)]
        for i in range(dim): I[i][i] = 1.0
        self.arms: Dict[str,Arm] = {
            'control': Arm('control', [0.0]*dim, [row[:] for row in I], [0.0]*dim),
            'canary':  Arm('canary',  [0.0]*dim, [row[:] for row in I], [0.0]*dim),
        }

    def sample_theta(self, arm: Arm) -> list[float]:
        # Gaussian approx; sample from N(theta, alpha^2 * A^{-1}) with diagonal-only for speed
        theta = []
        for i,w in enumerate(arm.theta):
            var = self.alpha / max(1e-6, arm.A[i][i])
            theta.append(random.gauss(w, var))
        return theta

    def choose(self, x: list[float]) -> str:
        vals = {}
        for name, arm in self.arms.items():
            th = self.sample_theta(arm)
            vals[name] = sum(th[i]*x[i] for i in range(self.dim))
        return max(vals, key=vals.get)

    def update(self, name: str, x: list[float], r: float):
        arm = self.arms[name]
        # Online ridge regression update (diagonal approx)
        for i in range(self.dim):
            arm.A[i][i] += x[i]*x[i]
            arm.b[i] += x[i]*r
            arm.theta[i] = arm.b[i] / max(1e-6, arm.A[i][i])

# Registry of per-domain bandits
BANDITS: Dict[str, CTS] = {}

def bandit_for(domain: str, dim: int) -> CTS:
    if domain not in BANDITS:
        BANDITS[domain] = CTS(dim)
    return BANDITS[domain]
```

**Router hook** (in `router_core.py`) — form a small context vector `x` from domain features; pick arm; map arms to treatment params (e.g., threshold, model bias). After outcome known, compute reward and `update()`.

**Reward computation** (in `eval_service/analyzers.py`)
```python
# reward R = a*success - b*cost - g*latency (normalize cost to USD, latency seconds)
DEFAULT_A, DEFAULT_B, DEFAULT_G = 1.0, 0.5, 0.1

def reward(success: bool, cost_usd: float, latency_ms: int, a=DEFAULT_A, b=DEFAULT_B, g=DEFAULT_G):
    return (1.0 if success else 0.0) - b*float(cost_usd or 0.0) - g*float(latency_ms or 0)/1000.0
```

**Eval API** (`/eval_service/app.py` additions)
```python
@app.post('/reward')
async def ingest_reward(r: dict):
    # store (trace_id, domain, arm, x, R) for offline analysis if desired
    return {'ok': True}

@app.get('/domain_stats')
async def domain_stats(domain: str):
    # aggregate success/cost/latency per arm for dashboards (omitted for brevity)
    return {"domain": domain}
```

---

## 3) Route DAGs (Pipeline Routing)

Choose the **whole** pipeline, not just the model: `retriever → reranker → context_budget → model → validators`.

**Spec** (`/docs/ROUTE_DAG_SPEC.md`)
```yaml
version: 1
pipeline:
  - id: retrieve
    with: bm25         # bm25|dense|hybrid
    params: { top_k: 50 }
  - id: rerank
    with: crossenc     # none|crossenc
    params: { top_k: 8 }
  - id: context
    with: budget
    params: { tokens: 2800 }
  - id: model
    with: auto         # mistral-small|gpt-5|claude-3-7|auto
  - id: validate
    with: rag_default  # domain preset
```

**Engine** (`/router/app/dag.py`)
```python
from typing import Dict, Any

class Stage:
    async def run(self, ctx: Dict[str,Any]):
        return ctx

class Retrieve(Stage):
    async def run(self, ctx):
        # call KB/search; attach ctx['hits']
        return ctx

class Rerank(Stage):
    async def run(self, ctx):
        # optional cross-encoder rerank
        return ctx

class ContextBudget(Stage):
    async def run(self, ctx):
        # trim hits/content to token budget
        return ctx

class ModelCall(Stage):
    async def run(self, ctx):
        # call router/providers based on ctx['chosen_model']
        return ctx

STAGES = {
  'retrieve': Retrieve,
  'rerank': Rerank,
  'context': ContextBudget,
  'model':   ModelCall
}

async def run_dag(recipe: list[dict], ctx: Dict[str,Any]):
    for step in recipe:
        cls = STAGES.get(step['id'])
        if not cls: continue
        s = cls()
        ctx = await s.run(ctx)
    return ctx
```

**Routing**: For each domain, define a default recipe YAML; the bandit can switch recipes (e.g., `crossenc` on/off, different context budgets) as its “arms.”

---

## 4) SLO‑Aware Cascades (Brownouts)

If a tenant’s rolling p95 latency exceeds the SLO, gradually **brownout** to cheaper/shallower routes: reduce context budget, disable rerank, or pick a cheaper model. Always respect OPA policies.

**`/router/app/slo.py`**
```python
import time, collections
from typing import Dict

WINDOW = 300  # seconds

class SLO:
    def __init__(self, target_ms: int):
        self.target = target_ms
        self.samples = collections.deque()  # (ts, latency_ms)
    def add(self, lat_ms: int):
        now = time.time()
        self.samples.append((now, lat_ms))
        while self.samples and (now - self.samples[0][0] > WINDOW):
            self.samples.popleft()
    def p95(self) -> int:
        arr = [l for _,l in self.samples]
        if not arr: return 0
        arr.sort()
        idx = max(0, int(0.95*len(arr))-1)
        return arr[idx]
    def brownout_level(self) -> int:
        p = self.p95()
        if p <= self.target: return 0
        if p <= 1.1*self.target: return 1
        if p <= 1.3*self.target: return 2
        return 3

TENANT_SLOS: Dict[str,SLO] = {}

def slo_for(tenant: str, target_ms: int) -> SLO:
    if tenant not in TENANT_SLOS:
        TENANT_SLOS[tenant] = SLO(target_ms)
    return TENANT_SLOS[tenant]
```

**Router usage**: After each request, record latency into `slo_for(tenant)`. Before building the DAG, read `brownout_level()` and adjust the recipe:
- L1: shrink `tokens` to 60%
- L2: disable rerank
- L3: force `mistral-small` (unless policy forbids)

Expose Prometheus gauges `slo_p95_ms{tenant}` and counters `brownout_level{tenant}`.

---

## 5) KPIs & Dashboards

Prometheus metrics (in `metrics.py`):
```python
from prometheus_client import Counter, Gauge, Histogram

cost_per_success = Gauge('router_cost_per_success','USD per accepted answer',['domain'])
quality_delta    = Gauge('router_quality_delta','Δ quality vs baseline',['domain'])
latency_p95      = Gauge('router_latency_p95_ms','p95 latency ms',['domain','tenant'])

# Update after outcome aggregation (periodic task) and per-request latency samples
```

Dashboards:
- **Horizon1 KPIs**: `cost_per_success` trend; `latency_p95` vs SLO; validator pass rate vs baseline (quality delta).
- **Bandit**: arm share over time, estimated reward, cumulative regret.
- **SLO**: p95 per tenant, brownout level history, success rate during brownouts.

---

## 6) Router Core Wiring (high-level)

**`router_core.py` key flow**
```python
# 1) detect domain → extract domain features
# 2) build context vector x (few normalized features)
# 3) ask bandit for arm → map to treatment (thresholds, recipe choice, model bias)
# 4) construct DAG recipe (domain default ± brownout adjustments ± treatment)
# 5) run DAG (retrieve → rerank → context → model)
# 6) validate (domain validators) → cascade if fail (respect SLO & OPA)
# 7) log latency/cost/outcome; compute reward; update bandit; push to eval_service
```

---

## 7) Acceptance Criteria

- **Cost per successful task ↓ ≥30%** (Prometheus `cost_per_success`) vs baseline week.
- **p95 latency ↓ ≥10%** per domain and tenant; brownouts stay <10% of requests.
- **Quality Δ within ±2%** of baseline validator pass rate.
- **Bandit stability**: exploration <20% after warm‑up; regret slope flattens.

---

## 8) Rollout Plan

1) **Shadow**: enable domain detectors + validators without affecting routes; log would‑be decisions.  
2) **10% canary**: bandit on `recipe: {rerank on/off}`; brownout disabled; monitor.  
3) **Add brownouts**: enforce SLO steps; verify tenants unaffected by others.  
4) **Expand**: add model bias arms; enable per‑domain recipes.  
5) **Ship**: set canary → 100% and freeze config snapshots for audit.

---

## 9) Notes

- Keep OPA as the hard brake (models, egress, budgets); bandit/DAG never override policy.  
- Persist bandit state per domain daily; warm‑start from eval DB aggregates.  
- For heavy‑duty classifiers, keep them tiny—never spend more to route than to answer.
```

