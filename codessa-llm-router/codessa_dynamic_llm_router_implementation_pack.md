# Codessa Dynamic LLM Router — Implementation Pack

This pack implements the recommended actions for dynamic LLM routing in Codessa, ready to run locally alongside your existing gateway. It includes a layered router, semantic cache, provider fallbacks via OpenRouter/Glama, OPA policy checks, a RouteLLM training pipeline, and an offline evaluation harness.

> All code is minimal and composable. Swap stubs with your production services without changing contracts.

---

## 0) Repo layout

```
/router
  /app
    main.py                 # HTTP service (FastAPI)
    registry.py             # Model registry & fingerprints
    features.py             # Feature extraction for router
    router_core.py          # L0/L1/L2/L3 decision stack
    providers/
      openrouter.py
      glama.py
      openai.py
      anthropic.py
      ollama.py
    cache.py                # Semantic + exact cache (Redis)
    policy.py               # OPA integration
    quality.py              # Post-gen quality checks, cascade gate
    metrics.py              # Prometheus/OpenTelemetry hooks
  requirements.txt
  models.yaml               # Model registry (editable)

/training
  route_dataset.md          # Dataset spec
  prepare_dataset.py        # Build training data from logs/evals
  train_router.py           # RouteLLM-based training
  evaluate_router.py        # Offline eval + RouterBench-style curves

/ops
  docker-compose.yml        # Router + Redis + example providers
  .env.example
  Makefile

/docs
  API.md                    # REST contract
```

---

## 1) API Contract (docs/API.md)

### POST `/chat-completions`
OpenAI-compatible request, with optional routing hints.
```json
{
  "model": "auto|gpt-5|claude-3-7|...",
  "messages": [{"role":"user","content":"..."}],
  "temperature": 0.2,
  "metadata": {
    "session": "<uuid>",
    "routingHints": {"domain":"code|qa|rag", "max_latency_ms": 3000, "budget_usd": 0.01}
  }
}
```
Returns OpenAI-ish response with `cost`, `route`, and `trace_id` attached.

### POST `/route`
Dry-run route only (no generation). Returns chosen model, policy decision, and estimated cost/latency.

---

## 2) Model registry (router/models.yaml)

```yaml
models:
  - id: gpt-5
    provider: openrouter
    price_per_1k_prompt: 0.005
    price_per_1k_completion: 0.015
    max_tokens: 16384
    tags: [strong, general]
  - id: claude-3-7
    provider: openrouter
    price_per_1k_prompt: 0.004
    price_per_1k_completion: 0.012
    max_tokens: 200k
    tags: [strong, long, code]
  - id: mistral-small
    provider: openrouter
    price_per_1k_prompt: 0.0002
    price_per_1k_completion: 0.0006
    tags: [cheap]
  - id: llama3.1
    provider: ollama
    tags: [local, cheap]
  - id: gemini-1.5-pro
    provider: glama
    tags: [strong, vision]
```

---

## 3) Router service (router/app/main.py)

```python
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from .registry import ModelRegistry
from .policy import opa_allow
from .router_core import decide_model, generate_with_model
from .cache import SemanticCache
from .metrics import Meter
import os, uuid

app = FastAPI(title="Codessa Dynamic LLM Router")
REG = ModelRegistry.from_yaml(os.getenv("MODEL_REGISTRY", "router/models.yaml"))
CACHE = SemanticCache(url=os.getenv("REDIS_URL","redis://redis:6379/0"))
METER = Meter()

class Msg(BaseModel):
    role: str
    content: str

class ChatReq(BaseModel):
    model: str|None = "auto"
    messages: list[Msg]
    temperature: float|None = 0.2
    metadata: dict|None = None

@app.post("/chat-completions")
async def chat(req: ChatReq, request: Request):
    trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
    session = (req.metadata or {}).get("session")
    # L0: policy gate
    if not await opa_allow("codessa.model", {
        "user": request.headers.get("x-user-id","phoenix"),
        "model": req.model,
        "session": {"id": session, "scopes": request.headers.get("x-scopes","" ).split(",")},
        "request": {"path":"/chat-completions"}
    }):
        raise HTTPException(403, "Model not allowed by policy")

    # Cache check (exact & semantic)
    user_text = next((m.content for m in reversed(req.messages) if m.role=="user"), "")
    cached = await CACHE.get(user_text)
    if cached:
        METER.log(trace_id, route="cache", model="cache", cost=0.0, ok=True)
        return cached | {"route": {"decision":"cache"}, "trace_id": trace_id}

    # L1/L2: decide model (deterministic + learned)
    decision = await decide_model(req, REG)

    # L3: generate + quality gate + possible cascade
    result = await generate_with_model(req, decision, REG, trace_id)

    # cache success
    if result.get("ok"):
        await CACHE.put(user_text, result)

    # metrics
    METER.log(trace_id, route=decision["decision"], model=decision["model"], cost=result.get("cost",{}).get("estimated_usd",0.0), ok=result.get("ok", True))

    result.update({"route": decision, "trace_id": trace_id})
    return result

@app.post("/route")
async def route_only(req: ChatReq, request: Request):
    decision = await decide_model(req, REG)
    return {"route": decision, "trace_id": str(uuid.uuid4())}
```

---

## 4) Decision stack (router/app/router_core.py)

```python
from .features import extract_features
from .providers import openrouter as OR, glama as GL, openai as OAI, anthropic as AN, ollama as OL
from .quality import should_escalate

async def decide_model(req, REG):
    # L1: deterministic heuristics
    feats = extract_features(req)
    if feats["is_trivial"] and feats["short"]:
        return {"decision":"l1-heuristic","model":"mistral-small","reason":"trivial+short"}
    if feats["needs_long_context"]:
        return {"decision":"l1-heuristic","model":"claude-3-7","reason":"long-context"}
    if feats["is_code"]:
        return {"decision":"l1-heuristic","model":"claude-3-7","reason":"code"}
    # L2: learned router (placeholder: linear score)
    # Plug RouteLLM inference here; for now, choose strong vs cheap
    model = "gpt-5" if feats["complex"] else "mistral-small"
    return {"decision":"l2-learned","model": model, "reason":"complex" if feats["complex"] else "simple"}

async def call_provider(model_id, payload, REG):
    prov = REG.provider_for(model_id)
    if prov == "openrouter":
        return await OR.chat(model_id, payload)
    if prov == "glama":
        return await GL.chat(model_id, payload)
    if prov == "openai":
        return await OAI.chat(model_id, payload)
    if prov == "anthropic":
        return await AN.chat(model_id, payload)
    if prov == "ollama":
        return await OL.chat("llama3.1", payload)
    raise RuntimeError("unknown provider")

async def generate_with_model(req, decision, REG, trace_id):
    payload = {"model": decision["model"], "messages": [m.dict() for m in req.messages], "temperature": req.temperature}
    # first attempt
    resp = await call_provider(decision["model"], payload, REG)
    ok, reason = should_escalate(req, resp)
    if ok:
        return resp | {"ok": True}
    # cascade once to strong model
    fallback = "gpt-5" if decision["model"] != "gpt-5" else "claude-3-7"
    resp2 = await call_provider(fallback, payload | {"model": fallback}, REG)
    return resp2 | {"ok": True, "cascade_from": decision["model"], "cascade_to": fallback}
```

---

## 5) Providers (router/app/providers/openrouter.py)

```python
import os, aiohttp
BASE = os.getenv("OPENROUTER_BASE","https://openrouter.ai/api/v1")
KEY  = os.getenv("OPENROUTER_API_KEY")

async def chat(model, payload):
    async with aiohttp.ClientSession() as s:
        p = {"model": model, "messages": payload["messages"], "temperature": payload.get("temperature",0.2)}
        h = {"Authorization": f"Bearer {KEY}", "Content-Type":"application/json"}
        async with s.post(f"{BASE}/chat/completions", json=p, headers=h, timeout=120) as r:
            j = await r.json()
            j.setdefault("cost", {"estimated_usd": 0.0})
            return j
```

(Analogous modules for `glama.py`, `openai.py`, `anthropic.py`, `ollama.py` with small differences in URLs/headers.)

---

## 6) Semantic cache (router/app/cache.py)

```python
import aioredis, hashlib, json

class SemanticCache:
    def __init__(self, url):
        self.r = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    async def key(self, text:str):
        # Simple hash; swap with embedding-based ANN key if desired
        return "ccache:" + hashlib.sha256(text.strip().lower().encode()).hexdigest()
    async def get(self, text):
        k = await self.key(text)
        raw = await self.r.get(k)
        return json.loads(raw) if raw else None
    async def put(self, text, obj, ttl=3600):
        k = await self.key(text)
        await self.r.set(k, json.dumps(obj), ex=ttl)
```

---

## 7) Quality checks & cascade (router/app/quality.py)

```python
import re

def should_escalate(req, resp):
    # Simple proxies; replace with task-specific checks
    text = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    if len(text.strip()) < 10:
        return (False, "too_short")
    # if RAG intent: require at least one citation marker like [1] or kb://
    intent = (req.metadata or {}).get("routingHints", {}).get("domain")
    if intent == "rag" and not ("kb://" in text or re.search(r"\[[0-9]+\]", text)):
        return (False, "no_citations")
    return (True, None)
```

---

## 8) OPA integration (router/app/policy.py)

```python
import os, aiohttp
OPA = os.getenv("OPA_URL", "http://opa:8181")

async def opa_allow(pkg: str, inp: dict) -> bool:
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{OPA}/v1/data/{pkg}/allow", json={"input": inp}, timeout=10) as r:
            j = await r.json()
            return bool(j.get("result", False))
```

Example Rego (expand in your OPA bundle):
```rego
package codessa.model

default allow = false
allow { input.model == "auto" }
allow { input.model == "mistral-small" }
allow { input.user == "phoenix"; input.model == "gpt-5" }
```

---

## 9) Metrics (router/app/metrics.py)

```python
from prometheus_client import Counter

route_count = Counter('router_requests_total', 'Requests', ['route','model','ok'])
route_cost  = Counter('router_cost_usd_total', 'Cost USD', ['model'])

class Meter:
    def log(self, trace_id, route, model, cost, ok):
        route_count.labels(route, model, str(ok)).inc()
        route_cost.labels(model).inc(cost)
```

Expose Prometheus at `/metrics` via `prometheus_client.start_http_server` if desired.

---

## 10) Feature extraction (router/app/features.py)

```python
import re

def extract_features(req):
    text = "\n".join([m.content for m in req.messages if m.role in ("system","user","assistant")]).lower()
    return {
        "len": len(text),
        "short": len(text) < 240,
        "is_trivial": len(text) < 120 and text.endswith("?"),
        "is_code": any(k in text for k in ["def ","class ","package.json","stacktrace","traceback","diff","+++ b/","--- a/"]),
        "needs_long_context": sum(w in text for w in ["full file","long transcript","many pages","book chapter"])>0,
        "complex": sum(w in text for w in ["design","prove","optimize","refactor","security","compliance","multi-agent"])>0,
    }
```

---

## 11) Training pipeline (training/route_dataset.md)

**Goal:** Train a pre-generation router that predicts **cheap vs strong** (and later N-way) using your own data.

**Input sources:**
- Gateway logs: `{messages[], model_used, latency_ms, cost_usd}`
- Outcome labels: for code tasks → unit test pass; for QA → preference wins; for RAG → citation faithfulness.

**Unified record (JSONL):**
```json
{
  "messages": [{"role":"user","content":"..."}],
  "domain": "code|rag|qa|chat",
  "gold": {"cheap_ok": true, "strong_ok": true},
  "features": {"len": 512, "is_code": true, ...}
}
```

**Labeling rule (binary first):**
- `label=0` if cheap model answer acceptable; else `label=1` (needs strong).

---

## 12) Prepare data (training/prepare_dataset.py)

```python
import json, sys

# Convert logs + evals into (X,y)
with open(sys.argv[1]) as f:
    for line in f:
        rec = json.loads(line)
        label = 1 if not rec["gold"]["cheap_ok"] else 0
        out = {
            "text": rec["messages"][-1]["content"],
            "features": rec.get("features", {}),
            "label": label,
            "domain": rec.get("domain","chat")
        }
        print(json.dumps(out))
```

---

## 13) Train with RouteLLM (training/train_router.py)

```python
# Skeleton — swap with RouteLLM training API of your choice
# Strategy: fine-tune a small classifier over features or embeddings.
import json, sys
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

texts, labels = [], []
for line in sys.stdin:
    r = json.loads(line)
    texts.append(r["text"])  # basic; can concat engineered features
    labels.append(r["label"])

X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42)
vec = TfidfVectorizer(max_features=50000, ngram_range=(1,2))
clf = LogisticRegression(max_iter=200)
Xtr = vec.fit_transform(X_train)
Xte = vec.transform(X_test)
clf.fit(Xtr, y_train)
print("F1:", f1_score(y_test, clf.predict(Xte)))
# Persist model via joblib; load in router_core for L2
```

(When you switch to RouteLLM proper, replace this with their router model and inference API.)

---

## 14) Offline eval (training/evaluate_router.py)

```python
# Produce cost–quality curves by simulating routes over a held-out set.
# Compute: cost_savings vs quality_drop; plot and export CSV for dashboards.
```

---

## 15) Docker Compose (ops/docker-compose.yml)

```yaml
version: '3.9'
services:
  redis:
    image: redis:7
    ports: ["6379:6379"]
  opa:
    image: openpolicyagent/opa:latest
    command: ["run","--server","/policies"]
    volumes:
      - ./opa:/policies:ro
    ports: ["8181:8181"]
  router:
    build: ../router
    environment:
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      OPENROUTER_BASE: https://openrouter.ai/api/v1
      GLAMA_API_KEY: ${GLAMA_API_KEY}
      OPA_URL: http://opa:8181
      REDIS_URL: redis://redis:6379/0
      MODEL_REGISTRY: /app/models.yaml
    ports: ["8090:80"]
    depends_on: [redis, opa]
```

**.env.example**
```
OPENROUTER_API_KEY=
GLAMA_API_KEY=
```

**Makefile**
```make
up:
	cd ops && docker compose up -d --build

down:
	cd ops && docker compose down -v

logs:
	cd ops && docker compose logs -f router
```

---

## 16) Smoke tests

```bash
# Route-only dry run
curl -sX POST localhost:8090/route -H 'content-type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"Generate a unit test for this diff: --- a/x +++ b/x"}]}' | jq

# Chat with routing
curl -sX POST localhost:8090/chat-completions -H 'content-type: application/json' \
  -H 'x-user-id: phoenix' -H 'x-scopes: docs.rag,git.write' \
  -d '{"model":"auto","messages":[{"role":"user","content":"Summarize SOLID principles"}],"metadata":{"routingHints":{"domain":"qa"}}}' | jq
```

---

## 17) Integration with Codessa Gateway

Point the gateway’s `/llm/chat-completions` to `http://router:80/chat-completions`. Keep OPA at the edge as well; this router performs a second pass for model-specific checks if desired.

---

## 18) Next upgrades (drop-in)

- Replace TF-IDF classifier with **RouteLLM** router; store weights and features in the repo.
- Add **semantic cache** using embeddings + ANN (we currently hash; swap with pgvector or Redis-Search vectors).
- Attach **OpenTelemetry** spans and expose Prometheus `/metrics`.
- Expand **cascade** with task-aware checks (code unit tests, RAG faithfulness, toxicity/safety gates).
- Weekly **model fingerprinting** job: score fleet on a probe set and update `models.yaml` with fresh priors.
```

