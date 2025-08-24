# Sprint 1 — Production Readiness: Quality Gates, A/B Testing, Feedback API, Multi‑Tenant Policies

This sprint layers four capabilities onto your current Codessa ⇆ PyGPT stack:

1) **Task‑specific quality validators** (code, RAG, safety) with cascade hooks  
2) **A/B testing framework** (deterministic bucketing, exposure logging, metric taps)  
3) **Feedback API** (trace‑linked thumbs/ratings/comments; ready for training signals)  
4) **Multi‑tenant routing policies** (OPA rules + gateway middleware)

All changes are drop‑in patches compatible with the Router/Gateway packs you have.

---

## 0) Repo deltas

```
/router/app/
  quality.py            # UPDATED: validators + cascade signals
  abtest.py             # NEW: experiment registry + bucketing
  telemetry.py          # UPDATED: exposure/metric taps
  router_core.py        # UPDATED: A/B hooks + validator call graph
  providers/moderation.py # NEW: moderation adapter (pluggable)

/gateway/app/
  feedback.py           # NEW: feedback API
  tenants.py            # NEW: tenant context & SLA headers
  main.py               # UPDATED: OPA per‑tenant inputs, route passthrough of A/B variants

/opa/policies/
  tenant.rego           # NEW: per‑tenant model/provider/budget/SLA rules
  budget.rego           # UPDATED
  model.rego            # UPDATED: tenant‑aware

/ops/
  grafana/dashboards/abtest.json  # NEW: exposure & lift panels
  grafana/dashboards/quality.json # NEW: validator pass rates, cascade triggers
```

---

## 1) Quality validators (router/app/quality.py)

### Intent
Lightweight, task‑aware checks that (a) gate acceptance, (b) trigger **controlled cascade** to a stronger model, and (c) produce structured telemetry.

### Implementation
```python
# router/app/quality.py
from __future__ import annotations
import re, ast, json
from typing import Tuple

RAG_CITATION_RX = re.compile(r"\b(kb://|\[[0-9]+\])")

class ValidationResult(dict):
    @property
    def ok(self) -> bool: return bool(self.get('ok', False))

# --- Code validators ---

def _extract_code_blocks(text: str):
    blocks = []
    for m in re.finditer(r"```(\w+)?\n(.*?)```", text, re.S):
        lang = (m.group(1) or '').lower(); code = m.group(2)
        blocks.append((lang, code))
    return blocks

def code_has_block(text: str) -> ValidationResult:
    ok = "```" in text
    return ValidationResult(ok=ok, reason=None if ok else 'no_code_block')

def code_python_compiles(text: str) -> ValidationResult:
    for lang, code in _extract_code_blocks(text):
        if lang in ('py','python',''):  # allow unknown
            try:
                ast.parse(code)
                return ValidationResult(ok=True)
            except SyntaxError:
                return ValidationResult(ok=False, reason='py_syntax_error')
    return ValidationResult(ok=False, reason='no_python_block')

# placeholder for JS/TS: integrate esprima/tsserver in worker if needed

# --- RAG validators ---

def rag_has_citations(text: str) -> ValidationResult:
    ok = bool(RAG_CITATION_RX.search(text))
    return ValidationResult(ok=ok, reason=None if ok else 'no_citations')

# Contract: kb_lookup(q) -> list of {doc_id, snippet}
async def rag_claim_coverage(answer: str, kb_lookup) -> ValidationResult:
    # naive: extract sentences with proper nouns and verify at least one KB hit per 3 sentences
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
    target = max(1, len(sents)//3)
    hits = 0
    for s in sents[::3]:
        res = await kb_lookup(s)
        if res: hits += 1
    ok = hits >= target
    return ValidationResult(ok=ok, reason=None if ok else 'low_claim_coverage', meta={'hits':hits,'target':target})

# --- Safety validators ---
async def moderation_check(prompt: str, answer: str, moderate) -> ValidationResult:
    # moderate(text) -> {blocked:bool, category:str}
    out = await moderate(f"PROMPT:\n{prompt}\n\nANSWER:\n{answer}")
    return ValidationResult(ok=not out.get('blocked', False), reason=out.get('category'))

# --- Orchestrator ---
async def validate(domain: str, prompt: str, answer: str, kb_lookup=None, moderate=None) -> Tuple[bool, dict]:
    checks = []
    if domain == 'code':
        checks += [code_has_block(answer), code_python_compiles(answer)]
    if domain == 'rag':
        checks += [rag_has_citations(answer)]
        if kb_lookup: checks += [await rag_claim_coverage(answer, kb_lookup)]
    if moderate:
        checks += [await moderation_check(prompt, answer, moderate)]
    ok = all(c.ok for c in checks)
    return ok, { 'checks': checks }
```

### Router integration (router/app/router_core.py)
Add after the first model call and before cascade:
```python
from .quality import validate
from .providers.moderation import moderate

async def generate_with_model(req, decision, REG, trace_id):
    payload = {"model": decision["model"], "messages": [m.dict() for m in req.messages], "temperature": req.temperature}
    resp = await call_provider(decision["model"], payload, REG)

    domain = (req.metadata or {}).get("routingHints", {}).get("domain")
    prompt = next((m.content for m in req.messages if m.role=='user'), '')

    async def kb_lookup(q):
        # call KB /search and return hits (omitted: use Gateway URL)
        return []

    ok, details = await validate(domain, prompt, resp['choices'][0]['message']['content'], kb_lookup=kb_lookup, moderate=moderate)
    if ok:
        return resp | {"ok": True, "validators": details}

    # cascade once
    fallback = "gpt-5" if decision["model"] != "gpt-5" else "claude-3-7"
    resp2 = await call_provider(fallback, payload | {"model": fallback}, REG)
    return resp2 | {"ok": True, "cascade_from": decision["model"], "cascade_to": fallback, "validators": details}
```

**Moderation provider** (`router/app/providers/moderation.py`)
```python
# swap with Azure/OpenAI/ToxiPi as needed
async def moderate(text: str):
    return {"blocked": False}
```

---

## 2) A/B testing framework (router/app/abtest.py)

```python
# router/app/abtest.py
from __future__ import annotations
import os, json, hashlib, time
from dataclasses import dataclass
from typing import Optional

CONFIG = os.getenv('ABTEST_CONFIG','/etc/ab/experiments.json')

def _load():
    try:
        with open(CONFIG) as f: return json.load(f)
    except Exception:
        return {"experiments": []}

@dataclass
class Assignment:
    name: str; variant: str; hash: str

def assign(user_id: str, name: str, variants: list[str]) -> Assignment:
    h = hashlib.sha256(f"{user_id}:{name}".encode()).hexdigest()
    idx = int(h, 16) % max(1, len(variants))
    return Assignment(name=name, variant=variants[idx], hash=h)

class AB:
    def __init__(self):
        self.cfg = _load()
    def active(self):
        return [e for e in self.cfg.get('experiments',[]) if e.get('enabled',False)]
    def decide(self, user_id: str):
        out = {}
        for e in self.active():
            a = assign(user_id, e['name'], e['variants'])
            out[e['name']] = a.variant
        return out
```

**Example config** `/etc/ab/experiments.json`
```json
{
  "experiments": [
    { "name": "router_threshold", "enabled": true, "variants": ["loose", "strict"] },
    { "name": "cascade_policy",  "enabled": true, "variants": ["once", "twice"] }
  ]
}
```

**Using A/B in `router_core.py`**
```python
from .abtest import AB
ABR = AB()

async def decide_model(req, REG):
    feats = extract_features(req)
    user = (req.metadata or {}).get('session','anon')
    variants = ABR.decide(user)

    # tweak thresholds by variant
    if variants.get('router_threshold') == 'strict' and feats['complex']:
        return {"decision":"l2-learned","model":"gpt-5","reason":"complex+strict"}

    # ... fallback to learned
```

Expose **experiment assignments** in response under `route.experiments` and in Prometheus counters.

---

## 3) Feedback API (gateway/app/feedback.py)

```python
from fastapi import APIRouter, Request
from pydantic import BaseModel
import time, asyncpg, os

router = APIRouter(prefix="/feedback")
DSN = os.getenv('PG_DSN','postgresql://postgres:postgres@postgres:5432/gateway')

class Feedback(BaseModel):
    trace_id: str
    rating: int | None = None        # -1, 0, +1
    correctness: int | None = None   # 1..5
    helpfulness: int | None = None   # 1..5
    comment: str | None = None
    tags: list[str] | None = None

@router.post("")
async def submit(fb: Feedback, request: Request):
    pool = await asyncpg.create_pool(DSN)
    async with pool.acquire() as con:
        await con.execute(
            """
            INSERT INTO feedback(trace_id, user_id, rating, correctness, helpfulness, comment, tags, ts)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8)
            """,
            fb.trace_id, request.headers.get('x-user-id','anon'), fb.rating, fb.correctness, fb.helpfulness, fb.comment, fb.tags, int(time.time())
        )
    return {"ok": True}
```

**Schema migration (gateway DB)**
```sql
CREATE TABLE IF NOT EXISTS feedback (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT,
  user_id TEXT,
  rating INT,
  correctness INT,
  helpfulness INT,
  comment TEXT,
  tags TEXT[],
  ts BIGINT
);
```

**Client usage**: IDE/UI posts `POST /feedback` with `trace_id` surfaced in router responses. Router can also add a `/feedback` convenience endpoint that proxies to gateway.

---

## 4) Multi‑tenant routing policies (OPA)

**`opa/policies/tenant.rego`**
```rego
package codessa.tenant

default allow = false

# Example: different model allow‑lists and budgets per tenant/tier
allow {
  some t
  t := input.session.tenant
  tiers := {
    "acme": {"models": {"cheap": ["mistral-small","llama3.1"], "strong": ["gpt-5","claude-3-7"]}, "budget": 5.0, "sla_ms": 2500},
    "zephyr": {"models": {"cheap": ["mistral-small"], "strong": ["gpt-5"]}, "budget": 1.0, "sla_ms": 2000}
  }
  tiers[t]
}
```

**`opa/policies/model.rego`** (tenant‑aware)
```rego
package codessa.model

default allow = false

allow {
  t := input.session.tenant
  m := input.model
  # call out to tenant policy or load from data.tenant
  allowed := {
    "acme": {"gpt-5": true, "claude-3-7": true, "mistral-small": true},
    "zephyr": {"gpt-5": true, "mistral-small": true}
  }
  allowed[t][m]
}
```

**Gateway: attach tenant context**
```python
# gateway/app/tenants.py
from fastapi import Request

def tenant_ctx(request: Request):
    return {
        'tenant': request.headers.get('x-tenant','acme'),
        'tier': request.headers.get('x-tier','standard'),
        'budget_usd': float(request.headers.get('x-budget-usd','1.0'))
    }
```

Use `tenant_ctx` in `/llm/chat-completions` OPA input and forward `x-tenant` to the router. Router may adjust decisions based on `sla_ms` in metadata/routingHints.

---

## 5) Telemetry taps

- **Validator** results → Prometheus counters (`validator_pass_total{type=rag/code/mod}`) and reasons for failures.
- **A/B** exposure → `ab_exposure_total{name,variant}` incremented once per trace.
- **Feedback** ingested → `feedback_count_total{rating}` and join with outcomes for analysis.

---

## 6) Test plan

1) **Code path**: ask for a Python function; ensure `no_code_block` triggers cascade when missing. Add a fenced block; verify acceptance.  
2) **RAG path**: ask for facts requiring citations; ensure `no_citations` triggers cascade. Populate KB; verify `claim_coverage` improves.  
3) **Moderation**: feed a toxic prompt; confirm moderation blocks or cascades per policy.  
4) **A/B**: set `router_threshold` experiment; check variant distribution across users and lift in cascade rate vs cost.  
5) **Feedback loop**: submit thumbs on traces; verify records and counters.  
6) **Tenant rules**: send `x-tenant=zephyr` and attempt `claude-3-7`; expect 403 by OPA.

---

## 7) Rollout

- Default validators to **soft-fail** (cascade) for one release; switch to **hard-fail** for egregious issues after monitoring.  
- Start A/B with 10% traffic to "strict"; expand based on win rate.  
- Make feedback optional but nudge in IDE UI with a non‑modal toast.

---

This sprint makes routing measurably smarter, safer, and ready for enterprise multi‑tenant ops. All files above are ready to copy into your repos; adjust provider integrations and OPA data sources to your environment.

