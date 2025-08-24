# Horizon 2 Pack — Multi‑Agent Routing, Memory Graph & Explainable Decisions

This pack upgrades Codessa from a model router into an **AI operations plane**: it can route **between agents**, ground answers on a **typed memory graph** with retrieval contracts, arbitrage providers via a **broker**, and surface **explainable decision cards**. It plugs into your existing gateway/router/eval/OPA stacks.

---

## 0) Repo layout (new & changed)

```
/agents/
  router/
    app.py                # Agent router service (contract‑net auction)
    registry.py           # Skill registry (capabilities, costs, SLOs)
    bidder.py             # Scoring/bidding logic
    contracts.py          # Agent capability schema; invocation contract
    metrics.py
  workers/
    code_dev.py           # Example specialist
    sec_review.py
    doc_writer.py

/memory_graph/
  schema.sql             # Graph tables (nodes/edges/properties)
  ingest.py              # Ingest from KB/GitHub/Docs into graph
  contracts.yaml         # Retrieval contract types (what evidence to fetch)
  query_api.py           # Graph traversal + evidence packs

/provider_broker/
  app.py                 # Provider exchange (price/health feed; policy‑aware bids)
  health.py              # Probes & SLAs
  pricing.py             # Static & dynamic pricing adapters

/router/app/
  dag.py                 # UPDATED: stages include `agent_call` & `graph_context`
  explain.py             # NEW: TraceLens explainers (priors, bandit, policy hits, DAG)
  registry.py            # UPDATED: read provider_broker baselines

/pygpt-ui/
  TraceLensPanel.tsx     # Explainable routing panel (deep dive)

/docs/
  AGENT_CONTRACTS.md     # Capability schema & scoring
  RETRIEVAL_CONTRACTS.md # How retrieval contracts bind to the graph
  PROVIDER_BROKER.md     # Price/health feed + hedging policy
  EXPLAINABILITY.md      # TraceLens data model
```

---

## 1) Agent Router (contract‑net style)

**Goal:** treat agents like models. A **router** solicits bids from registered agents based on capability + cost + SLO and selects the best bundle (possibly a sequence/DAG of agents).

**`/agents/router/contracts.py`**
```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class Capability(BaseModel):
    name: str             # e.g., code.generate_tests
    quality: float        # prior [0..1]
    cost_usd: float       # expected per task
    latency_ms: int
    constraints: Dict[str,str] = {}

class Bid(BaseModel):
    agent_id: str
    capability: str
    expected_quality: float
    expected_cost: float
    expected_latency: int
    plan: Dict            # optional steps/tools the agent will use

class Task(BaseModel):
    trace_id: str
    domain: str
    goal: str             # natural language intent
    inputs: Dict          # source refs, diffs, kb query, etc.
    sla_ms: int
    policy: Dict          # OPA‑derived constraints
```

**`/agents/router/registry.py`**
```python
import json, os
from typing import Dict, Callable

class Registry:
    def __init__(self):
        self._agents: Dict[str,Callable] = {}
        self._caps: Dict[str,dict] = {}
    def register(self, agent_id: str, fn: Callable, caps: dict):
        self._agents[agent_id] = fn
        self._caps[agent_id] = caps  # {capability: Capability}
    def capabilities(self):
        return self._caps
    def get(self, agent_id):
        return self._agents[agent_id]
```

**`/agents/router/bidder.py`**
```python
from .contracts import Task, Bid

def score(bid: Bid, task: Task, wq=0.6, wc=0.2, wl=0.2):
    # expected utility score with SLA penalty
    util = wq*bid.expected_quality - wc*bid.expected_cost - wl*(bid.expected_latency/1000)
    if bid.expected_latency > task.sla_ms:
        util -= 0.5
    return util

def choose(bids, task):
    ranked = sorted(bids, key=lambda b: score(b, task), reverse=True)
    return ranked[0]
```

**`/agents/router/app.py`**
```python
from fastapi import FastAPI
from .contracts import Task, Bid
from .registry import Registry
from .bidder import choose

app = FastAPI(title='Agent Router')
REG = Registry()

@app.post('/route')
async def route(task: Task):
    bids = []
    for aid, caps in REG.capabilities().items():
        if task.domain in caps.get('domains', ['chat']):
            capname = caps['capabilities'][0]['name']
            bids.append(Bid(agent_id=aid, capability=capname,
                            expected_quality=caps['capabilities'][0]['quality'],
                            expected_cost=caps['capabilities'][0]['cost_usd'],
                            expected_latency=caps['capabilities'][0]['latency_ms'],
                            plan={}))
    winner = choose(bids, task)
    return {'winner': winner.dict(), 'bids': [b.dict() for b in bids]}
```

**Gateway integration:** add `/agents/route` that forwards to agent router when the DAG includes `agent_call` stages.

---

## 2) Memory Graph & Retrieval Contracts

**Goal:** unify docs/repos/PRs/runs as a typed graph; retrieval contracts declare *what evidence* an answer must cite.

**Schema (`/memory_graph/schema.sql`)**
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS nodes (
  id BIGSERIAL PRIMARY KEY,
  type TEXT,          -- doc|code|issue|pr|run|person|org
  uri TEXT UNIQUE,    -- kb://doc/..., repo://org/repo#path, pr://...
  title TEXT,
  props JSONB,
  embedding VECTOR(1024)
);
CREATE TABLE IF NOT EXISTS edges (
  src BIGINT REFERENCES nodes(id),
  dst BIGINT REFERENCES nodes(id),
  type TEXT,          -- cites|implements|mentions|owner|authored
  props JSONB,
  PRIMARY KEY(src,dst,type)
);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_nodes_vec ON nodes USING ivfflat (embedding vector_cosine_ops);
```

**Retrieval contracts (`/memory_graph/contracts.yaml`)**
```yaml
contracts:
  rag.default:
    require:
      - type: doc
        relation: cites
        min_hits: 2
  code.patch_review:
    require:
      - type: code
        relation: implements
        min_hits: 1
      - type: pr
        relation: cites
        min_hits: 1
```

**Query API (`/memory_graph/query_api.py`)**
```python
# Given a contract + query text, return evidence pack: nodes + snippets + proofs (edge paths)
```

**Router DAG stage** — `graph_context`: resolves a contract into **evidence packs** and injects cite‑ready context; validators check that final answers reference returned URIs.

---

## 3) Provider Broker (price/health arbitrage)

**Goal:** centralize pricing/health and expose policy‑aware bids for the router.

**`/provider_broker/app.py`**
```python
from fastapi import FastAPI
from pydantic import BaseModel

class Quote(BaseModel):
    model: str
    price: float   # per 1k tokens USD
    latency_ms: int
    health: float  # 0..1

app = FastAPI(title='Provider Broker')

@app.get('/quotes')
async def quotes(models: str):
    # return best current quotes for comma‑separated model ids
    # source from pricing adapters + health probes
    return {'quotes':[{'model': m, 'price': 0.003, 'latency_ms': 800, 'health': 0.98} for m in models.split(',')]}
```

**Router integration:** when scoring candidates, weight with broker’s `price`/`health` and OPA policies (egress, budget, tenant allow‑list).

---

## 4) Explainable Decisions (TraceLens)

**Goal:** every route explains itself: priors, bandit/bids, policies hit, DAG recipe, evidence graph.

**`/router/app/explain.py`**
```python
from typing import Dict

def build_explanation(trace_id: str, meta: Dict) -> Dict:
    return {
      'trace': trace_id,
      'domain': meta.get('domain'),
      'priors': meta.get('priors'),
      'bandit': meta.get('bandit'),
      'policy': meta.get('policy_hits',[]),
      'dag': meta.get('dag_recipe'),
      'agent_bids': meta.get('agent_bids',[]),
      'evidence': meta.get('evidence',[]),
      'broker': meta.get('quotes',[])
    }
```

**UI (`/pygpt-ui/TraceLensPanel.tsx`)** — a collapsible pane under the assistant message that expands the RouteBadge into a full decision trail (no secrets, only IDs and metrics).

---

## 5) Router DAG extensions

**`/router/app/dag.py`** — add stages:
- `graph_context` → call memory_graph API with a contract; attach evidence
- `agent_call` → call Agent Router with a `Task`; stream progress/events

`recipe` can now include `agent_call` in place of `model` for certain domains.

---

## 6) OPA policies (agent & graph egress)

- **agent_capabilities.rego** — per‑tenant allow‑lists for which agents can execute `git.write`, `issue.create`, `sec.scan`.
- **graph_egress.rego** — disallow sending private graph nodes to public LLMs without waiver.

---

## 7) Metrics & Dashboards

New Prometheus counters/gauges:
- `agent_bid_count{agent,domain}` / `agent_win_rate{agent}`
- `graph_contract_satisfied{contract}`
- `broker_health_score{provider}`
- `explain_present_rate` (how many responses shipped with TraceLens)

Grafana seeds under `/ops/grafana/dashboards/*` with panels for bids, wins, graph coverage, and provider health.

---

## 8) Test Plan

1) **Agent routing**: submit a code‑fix task; verify bids; ensure the code_dev agent wins and produces PR with provenance.  
2) **Graph contracts**: ask a RAG question; confirm evidence nodes are included and citations reference `kb://` URIs returned by graph.  
3) **Broker**: simulate price spike; router switches to cheaper provider while staying within OPA policy.  
4) **Explainability**: open TraceLens; verify priors, bids, DAG, and policy hits are present.  
5) **Policies**: attempt `sec_review` for a tenant without scope; expect OPA 403.

---

## 9) Rollout

- Deploy Agent Router & Memory Graph as sidecars in staging; point router DAG stages at them.  
- Backfill graph via `ingest.py` (GitHub + KB) and cap size via sampling.  
- Keep TraceLens gated behind `TRACE_UI_ENABLED=true` until audit review.  
- Promote after one week of stable KPIs (cost/success unchanged, quality + explainability ↑).

---

This pack turns routing into **who + what + with which evidence**, then tells you exactly **why**. It’s designed to layer onto your Horizon‑1 system without breaking contracts or policies.

