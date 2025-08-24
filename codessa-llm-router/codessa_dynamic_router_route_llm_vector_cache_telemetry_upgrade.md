# Codessa Dynamic Router — RouteLLM + Vector Cache + Telemetry Upgrade

This upgrade layers **learned routing**, an **embedding‑based semantic cache (pgvector)**, and **end‑to‑end telemetry** onto the Dynamic LLM Router pack you already have. It is drop‑in compatible with your gateway contracts.

> Highlights
> - Pluggable **Learned Router** interface with two backends: (A) local linear/MLP classifier; (B) external RouteLLM service
> - **pgvector semantic cache** with similarity search + TTL + recency decay
> - **OpenTelemetry** traces + Prometheus metrics + Grafana dashboard seed
> - Policy‑aware routing with richer OPA inputs (budget/egress/tenant)

---

## 0) Files added/changed

```
/router/app/
  router_core.py          # UPDATED: learned router plug + cascade signals
  learned_router.py       # NEW: interface + local model + RouteLLM client
  cache.py                # UPDATED: pgvector semantic cache
  telemetry.py            # NEW: OpenTelemetry wiring + B3 propagation
  metrics.py              # UPDATED: histograms + gauges
  registry.py             # UPDATED: model fingerprints + priors
  quality.py              # UPDATED: task‑aware checks (RAG/code)

/router/sql/
  semantic_cache.sql      # NEW: pgvector schema for cache

/training/
  train_router_routeLLM.md   # NEW: notes for training with RouteLLM
  export_probe_fingerprints.py # NEW: weekly model fingerprint job

/ops/
  docker-compose.yml      # UPDATED: adds postgres + otel‑collector + grafana
  grafana/
    dashboards/router.json   # NEW: dashboard seed
  otel/
    collector.yaml           # NEW: OTLP→Prometheus/Grafana/Tempo (adjust)

/docs/
  TELEMETRY.md            # NEW: trace/cost/route fields & headers
```

---

## 1) Learned Router (pluggable)

**`/router/app/learned_router.py`**
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional
import os, json, aiohttp

Decision = dict  # {decision, model, reason, prob_strong}

@dataclass
class LearnedRouterConfig:
    backend: Literal['local','routellm'] = os.getenv('LEARNED_ROUTER','local')
    url: str = os.getenv('ROUTELLM_URL','http://router-ml:8081/route')

class LearnedRouter:
    def __init__(self, config: LearnedRouterConfig = LearnedRouterConfig()):
        self.cfg = config
        if self.cfg.backend == 'local':
            from joblib import load  # lazy
            import pathlib
            p = pathlib.Path(os.getenv('LOCAL_ROUTER_MODEL','/models/linear.joblib'))
            self.model = load(p) if p.exists() else None
            self.vectorizer = load(p.with_name('tfidf.joblib')) if p.with_name('tfidf.joblib').exists() else None

    async def predict(self, text: str, feats: dict) -> Decision:
        # Return probability that we need a STRONG model
        if self.cfg.backend == 'routellm':
            async with aiohttp.ClientSession() as s:
                payload = {"text": text, "features": feats}
                async with s.post(self.cfg.url, json=payload, timeout=10) as r:
                    j = await r.json()
                    p_strong = float(j.get('p_strong', 0.5))
        else:
            # local fallback: TFIDF + linear
            if self.model is None or self.vectorizer is None:
                p_strong = 0.5
            else:
                X = self.vectorizer.transform([text])
                p_strong = float(self.model.predict_proba(X)[0][1])
        reason = 'learned-strong' if p_strong >= 0.5 else 'learned-cheap'
        model = 'gpt-5' if p_strong >= 0.5 else 'mistral-small'
        return {"decision":"l2-learned","model": model, "reason": reason, "prob_strong": round(p_strong,3)}
```

**`/router/app/router_core.py`** (delta showing the learned hook)
```python
from .features import extract_features
from .learned_router import LearnedRouter
from .quality import should_escalate

LR = LearnedRouter()

async def decide_model(req, REG):
    feats = extract_features(req)
    # L1 heuristics
    if feats["is_trivial"] and feats["short"]:
        return {"decision":"l1-heuristic","model":"mistral-small","reason":"trivial+short"}
    if feats["needs_long_context"]:
        return {"decision":"l1-heuristic","model":"claude-3-7","reason":"long-context"}
    if feats["is_code"]:
        return {"decision":"l1-heuristic","model":"claude-3-7","reason":"code"}
    # L2 learned
    user_text = next((m.content for m in req.messages if m.role=='user'), '')
    return await LR.predict(user_text, feats)
```

**Optional RouteLLM inference microservice** (`/training/router_ml_server.py`)
```python
from fastapi import FastAPI
from pydantic import BaseModel
from joblib import load
import os

app = FastAPI()
VEC = load(os.getenv('VEC','/models/tfidf.joblib'))
CLF = load(os.getenv('CLF','/models/linear.joblib'))

class Req(BaseModel):
    text: str
    features: dict | None = None

@app.post('/route')
async def route(r: Req):
    X = VEC.transform([r.text])
    p = CLF.predict_proba(X)[0][1]
    return {"p_strong": float(p)}
```

---

## 2) pgvector Semantic Cache

**Schema** (`/router/sql/semantic_cache.sql`)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS semantic_cache (
  id BIGSERIAL PRIMARY KEY,
  key TEXT,               -- hash of normalized text
  text TEXT NOT NULL,     -- raw user text
  embedding VECTOR(1024), -- depends on your embedding model
  response JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  ttl_seconds INT DEFAULT 3600
);

CREATE INDEX IF NOT EXISTS idx_sem_cache_vec ON semantic_cache USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_sem_cache_ts ON semantic_cache (created_at);
```

**Cache module** (`/router/app/cache.py`) — updated to ANN search
```python
import asyncpg, hashlib, json, os
import aiohttp

EMBED_URL = os.getenv('EMBEDDINGS_URL')  # OpenAI‑style {input:[..]} → {data:[{embedding:[]}]}
PG_DSN = os.getenv('PG_DSN','postgresql://postgres:postgres@postgres:5432/router')
SIM_THRESHOLD = float(os.getenv('CACHE_SIM_THRESHOLD','0.92'))

class SemanticCache:
    def __init__(self, url=None):
        self.pool = None
    async def init(self):
        self.pool = await asyncpg.create_pool(PG_DSN)
    async def _embed(self, text:str):
        async with aiohttp.ClientSession() as s:
            async with s.post(EMBED_URL, json={"input":[text]}) as r:
                j = await r.json(); return j['data'][0]['embedding']
    async def get(self, text:str):
        if not self.pool: await self.init()
        emb = await self._embed(text)
        async with self.pool.acquire() as con:
            rows = await con.fetch(
                """
                SELECT response, 1 - (embedding <=> $1::vector) AS sim, created_at, ttl_seconds
                FROM semantic_cache
                WHERE now() - created_at < make_interval(secs => ttl_seconds)
                ORDER BY embedding <=> $1::vector ASC LIMIT 1
                """, emb)
        if not rows: return None
        row = rows[0]
        if float(row['sim']) >= SIM_THRESHOLD:
            return json.loads(row['response'])
        return None
    async def put(self, text:str, obj, ttl=3600):
        if not self.pool: await self.init()
        emb = await self._embed(text)
        async with self.pool.acquire() as con:
            await con.execute(
                "INSERT INTO semantic_cache(key,text,embedding,response,ttl_seconds) VALUES($1,$2,$3,$4,$5)",
                hashlib.sha256(text.strip().lower().encode()).hexdigest(), text, emb, json.dumps(obj), ttl
            )
```

**Wiring note:** call `await CACHE.init()` during router startup.

---

## 3) Telemetry

**`/router/app/telemetry.py`**
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
import os

OTLP = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT','http://otel-collector:4318')

def setup_otel(app):
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTLP}/v1/traces"))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    set_global_textmap(B3MultiFormat())
    FastAPIInstrumentor.instrument_app(app)
```

**`/router/app/main.py`** (telemetry init + header propagation)
```python
from .telemetry import setup_otel
...
app = FastAPI(title="Codessa Dynamic LLM Router")
setup_otel(app)
...
@app.post("/chat-completions")
async def chat(req: ChatReq, request: Request):
    trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
    # add headers on outbound provider calls too (propagate B3 if providers support)
    ...
```

**Prometheus metrics** (`/router/app/metrics.py`) — histograms and gauges
```python
from prometheus_client import Counter, Histogram, Gauge

route_count = Counter('router_requests_total','Requests',['route','model','ok'])
route_cost  = Counter('router_cost_usd_total','Cost',['model'])
latency     = Histogram('router_latency_seconds','Latency','model')
cache_hit   = Counter('router_cache_hits_total','semantic')
cascade_cnt = Counter('router_cascade_total','from','to')

class Meter:
    def log(self, trace_id, route, model, cost, ok, lat=None, cached=False, cascade=None):
        route_count.labels(route, model, str(ok)).inc()
        route_cost.labels(model).inc(cost)
        if lat is not None: latency.labels(model).observe(lat)
        if cached: cache_hit.inc()
        if cascade: cascade_cnt.labels(cascade['from'], cascade['to']).inc()
```

---

## 4) Model Registry: fingerprints + priors

**`/router/app/registry.py`** (delta)
```python
# Add fields: quality_prior, latency_ms, updated_at
# Provide REG.prior(model, domain) used by decide_model as a bias term
```

**Fingerprint job** (`/training/export_probe_fingerprints.py`)
```python
# Run weekly: score each model on a small probe set; write priors to models.yaml
```

---

## 5) Quality checks (task‑aware)

**`/router/app/quality.py`** (delta)
```python
import re

def should_escalate(req, resp):
    text = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    domain = (req.metadata or {}).get("routingHints", {}).get("domain")

    # Minimal acceptability
    if len(text.strip()) < 20: return (False, "too_short")

    # RAG: require citations or kb:// markers
    if domain == 'rag' and not ("kb://" in text or re.search(r"\[[0-9]+\]", text)):
        return (False, "no_citations")

    # Code: require fenced block present
    if domain == 'code' and '```' not in text:
        return (False, "no_code_block")

    return (True, None)
```

---

## 6) OPA inputs (richer)

At the router edge, send:
```json
{
  "user":"phoenix",
  "session":{"id":"...","tenant":"codessa","scopes":["git.write","docs.rag"],"budget_usd":1.00},
  "request":{"path":"/chat-completions","estimated_cost":0.0003},
  "context":{"private_docs": false}
}
```

Use this to block expensive models when budget is near zero; or to deny public LLMs when `context.private_docs=true` and no waiver.

---

## 7) Ops: Compose + Grafana + OTEL Collector

**`/ops/docker-compose.yml`** (appended services)
```yaml
  postgres:
    image: pgvector/pgvector:latest
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: router
    ports: ["5433:5432"]
    volumes:
      - pgdata_router:/var/lib/postgresql/data
      - ../router/sql/semantic_cache.sql:/docker-entrypoint-initdb.d/10_semantic_cache.sql

  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config","/etc/otel/collector.yaml"]
    volumes:
      - ./otel/collector.yaml:/etc/otel/collector.yaml:ro
    ports: ["4317:4317","4318:4318"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    volumes:
      - grafana:/var/lib/grafana
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin

volumes:
  pgdata_router: {}
  grafana: {}
```

**`/ops/otel/collector.yaml`** (minimal)
```yaml
receivers:
  otlp:
    protocols:
      http:
exporters:
  prometheus:
    endpoint: ":9464"
  logging: {}
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [logging]
```

**Grafana dashboard** (`/ops/grafana/dashboards/router.json`)
- Panels: requests by model, cost USD by model, latency histogram, semantic cache hit ratio, cascade rate, strong‑ratio over time, top routes.

---

## 8) Telemetry contract (docs/TELEMETRY.md)

- **Headers in**: `x-trace-id`, `x-session-id`, `x-user-id`, `x-scopes`
- **Fields out (response)**: `trace_id`, `route.decision`, `route.model`, `route.reason`, `route.prob_strong`, `cost.estimated_usd`, `cascade_from/to` (if any)
- **Spans**: `router.decide`, `router.generate`, `router.cascade`, `cache.hit`, provider spans `provider.openrouter.chat` …

---

## 9) Make it go

1) **Migrate** pgvector cache table:
```bash
cd ops && docker compose up -d postgres
# will auto-run semantic_cache.sql
```
2) **Bring up router + otel + grafana**:
```bash
export OPENROUTER_API_KEY=... GLAMA_API_KEY=... EMBEDDINGS_URL=http://your-embedder/v1/embeddings
make up
```
3) **Smoke tests** (semantic cache path):
```bash
# first call misses cache
curl -sX POST localhost:8090/chat-completions -H 'content-type: application/json' \
 -d '{"model":"auto","messages":[{"role":"user","content":"Explain SOLID principles succinctly."}],"metadata":{"routingHints":{"domain":"qa"}}}' | jq
# second call should hit cache (check /metrics for router_cache_hits_total)
```
4) **RouteLLM backend**: set `LEARNED_ROUTER=routellm` and run the small `router_ml_server.py` (or your RouteLLM service).

---

## 10) Acceptance checklist

- [ ] Learned router probabilities surface in `route.prob_strong`
- [ ] Semantic cache returns within 20ms for near-duplicates; hit ratio visible
- [ ] Cascade triggers when quality proxies fail; cascade counters increment
- [ ] OPA denies disallowed models; budget guard works
- [ ] Grafana shows request volume, latency, cost, cache hit ratio, cascade rate
- [ ] Weekly fingerprint job updates `models.yaml` priors

---

## 11) Next steps

- Swap TF‑IDF local classifier with a **RouteLLM** model trained on Codessa data; store weights in `/models` volume
- Add **per‑domain routers** (code, rag, qa) with specialized features/priors
- Implement **semantic cache write‑through** from gateway layer for shared cache across services
- Add **canary routing** (e.g., 5% traffic to experimental strong model) with outcome logging
- Integrate **Tempo/Jaeger** for trace persistence and link PRs/check runs with `trace_id`
```

