# Repo Drop: RFCs + Starter Scaffolds

**Date:** 2025-08-14
**Owner:** Platform Eng
**Status:** Proposed → Ready-to-merge (scaffolds included)
**Paths below are relative to repo root.**

---

## `/rfcs/RFC-001-taskspec.md`

**Title:** TaskSpec — Declarative Multi‑Step Jobs compiled to Temporal
**Author(s):** Platform Eng
**Status:** Proposed
**Last updated:** 2025-08-14

### Summary

A schema-first, declarative spec (JSON/YAML) for multi-step jobs (e.g., *Spec → Code → Test → QA*). The API compiles TaskSpecs to Temporal workflows. Benefits: deterministic execution, replay, clear contracts, and effortless pipeline composition.

### Motivation

Current multi-step flows are implicit in agent code and NATS subjects. This makes changes brittle, obscures policy enforcement, and complicates observability/replay.

### Proposal

* **TaskSpec** describes steps, routing, gates, policies, and schemas for step I/O.
* **Compiler** translates TaskSpec → Temporal DAG with activities for agent invocations.
* **Registry** stores versioned TaskSpecs.
* **Contracts** enforced with Pydantic/JSON Schema at the API boundary.

### Scope

* In: multi-step orchestration, schema validation, policy wiring, human-in-the-loop gates.
* Out: agent business logic, model selection (handled by Router, RFC‑002).

### Spec (abridged)

```yaml
# /specs/examples/doc_pipeline.yaml
apiVersion: maf/v1
kind: TaskSpec
metadata:
  name: doc_pipeline
  version: 1.0.0
  tenant: default
policies:
  maxCostUSD: 0.75
  deadline: 30m
  retries: {max: 2, backoff: exponential}
  dataScopes: ["public", "repo:docs"]
steps:
  - id: draft
    agent: doc_writer
    inputSchema: schemas/draft_in.schema.json
    outputSchema: schemas/draft_out.schema.json
  - id: compliance
    agent: compliance_checker
    inputFrom: draft
    gates:
      - type: human_review
        when: output.risk_score > 0.3
    outputSchema: schemas/compliance_out.schema.json
  - id: qa
    agent: qa_tester
    inputFrom: compliance
    outputSchema: schemas/qa_out.schema.json
```

### API Additions

```http
POST /tasks/from-spec
Body: { specRef: "doc_pipeline@1.0.0", input: { ... }, tenant: "default" }
```

### Rollout Plan

1. Land schema + compiler scaffolds. 2) Add endpoint + registry. 3) Migrate first pipeline. 4) Mark legacy flows deprecated.

### Security & Policy

* Evaluate OPA policies at: ingest, per-step tool calls, and egress.
* Per‑tenant encryption domain for persisted TaskSpec runs.

### Success Metrics

* 100% of multi-step jobs via TaskSpec by week 4.
* <5% failures from schema mismatches.
* Mean change time (adding a step) < 30 min.

---

## `/rfcs/RFC-002-router.md`

**Title:** Model Router — Cost/Latency/Quality‑Aware Dispatch with Experiments
**Author(s):** Platform Eng
**Status:** Proposed
**Last updated:** 2025-08-14

### Summary

Centralized router chooses a model per request given budgets (latency, cost) and quality tiers; supports A/B and multi‑armed bandits; respects per‑tenant policy.

### Motivation

Hard-coded models in agents increase cost, inhibit experiments, and complicate SLAs.

### Proposal

* **Policy-driven selection** via `models.yaml` (capabilities & priors) + `policies/model_router.yaml`.
* **Experiment engine** for shadowing and traffic splits.
* **Observability**: log decisions + realized metrics.

### Spec (abridged)

```yaml
# /config/models.yaml
models:
  - id: openai:gpt-4.1-mini
    family: gpt
    priors: {latency_ms_p50: 650, input_tok_usd: 0.0003, output_tok_usd: 0.0006}
    max_ctx: 128k
    quality: medium
  - id: openrouter:llama-3.1-70b
    family: llama
    priors: {latency_ms_p50: 900, input_tok_usd: 0.0001, output_tok_usd: 0.0002}
    max_ctx: 32k
    quality: medium
  - id: local:granite-20b
    family: granite
    priors: {latency_ms_p50: 220, input_tok_usd: 0.0, output_tok_usd: 0.0}
    max_ctx: 8k
    quality: draft
```

```yaml
# /policies/model_router.yaml
routing:
  default:
    latency_budget_ms: 2000
    cost_budget_usd: 0.002
    quality: medium
  tenants:
    acme-inc:
      quality: high
      cost_budget_usd: 0.01
experiments:
  - name: llama70b_vs_gptmini
    taskTypes: ["doc_draft"]
    trafficSplit: {control: 0.7, variant: 0.3}
    control: openai:gpt-4.1-mini
    variant: openrouter:llama-3.1-70b
    shadow: false
```

### API

Agents call: `router.select_model(task_type, tenant_id, request_hints)` → `{model_id, rationale, experiment?}`

### Rollout Plan

1. Land router lib + config. 2) Wrap a single agent. 3) Enable shadowing. 4) Expand to all agents.

### Success Metrics

* ≥20% median cost reduction without SLA regressions.
* Zero agent code changes needed for model swaps.
* At least one active experiment by week 6.

---

## `/rfcs/RFC-003-tracing-replay.md`

**Title:** Semantic Tracing & Deterministic Replay
**Author(s):** Platform Eng
**Status:** Proposed
**Last updated:** 2025-08-14

### Summary

End-to-end traces with semantic payloads (prompts, tools, retrievals, outputs, costs), persisted as immutable snapshots for one‑click deterministic replay.

### Motivation

Multi-agent debugging and quality control are slow without centralized semantic traces and reproducibility.

### Proposal

* **OpenTelemetry** spans with LLM-specific attributes.
* **Replay log** in S3/MinIO (content-addressed).
* **`replay(task_id)`** rehydrates prompts, seeds, retrieval, and tool outputs.

### Trace Schema (attrs excerpt)

```
maf.task.id, maf.step.id, maf.agent, maf.model.id, maf.prompt.sha256,
maf.retrieval.refs[], maf.tool.calls[], maf.output.sha256, maf.tokens.in/out,
maf.latency.ms, maf.cost.usd, maf.policy.snapshot
```

### Rollout Plan

1. Add OTel SDK + exporter. 2) Wrap agent I/O. 3) Persist snapshots. 4) Add CLI + UI button.

### Success Metrics

* 90% of bugs reproducible via `replay(task_id)`.
* MTTR ↓ 50%.
* ≥80% of traces contain full semantic payloads.

---

# Starter Scaffolds (drop‑in)

> These are thin, compilable stubs to unblock implementation. Keep them small and focused; tests prove wiring.

### 1) TaskSpec: schema, compiler, API

**`/specs/task_spec.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://maf/specs/task_spec.schema.json",
  "title": "TaskSpec",
  "type": "object",
  "required": ["apiVersion", "kind", "metadata", "steps"],
  "properties": {
    "apiVersion": {"type": "string"},
    "kind": {"const": "TaskSpec"},
    "metadata": {
      "type": "object",
      "required": ["name", "version"],
      "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "tenant": {"type": "string"}
      }
    },
    "policies": {"type": "object"},
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "agent"],
        "properties": {
          "id": {"type": "string"},
          "agent": {"type": "string"},
          "inputSchema": {"type": "string"},
          "outputSchema": {"type": "string"},
          "inputFrom": {"type": "string"},
          "gates": {"type": "array"}
        }
      }
    }
  }
}
```

**`/taskspec/compiler.py`**

```python
from __future__ import annotations
import json, pathlib
from pydantic import BaseModel, Field
from typing import List, Optional

class Step(BaseModel):
    id: str
    agent: str
    inputSchema: Optional[str] = None
    outputSchema: Optional[str] = None
    inputFrom: Optional[str] = None
    gates: Optional[list] = None

class TaskSpec(BaseModel):
    apiVersion: str
    kind: str = Field("TaskSpec", const=True)
    metadata: dict
    policies: dict | None = None
    steps: List[Step]

class CompiledWorkflow(BaseModel):
    name: str
    version: str
    steps: List[dict]

def compile_taskspec(spec_path: str | pathlib.Path) -> CompiledWorkflow:
    data = json.loads(pathlib.Path(spec_path).read_text()) if str(spec_path).endswith(".json") else _load_yaml(spec_path)
    spec = TaskSpec.model_validate(data)
    name = spec.metadata["name"]
    version = spec.metadata["version"]
    dag = []
    for s in spec.steps:
        dag.append({
            "id": s.id,
            "activity": "invoke_agent",
            "agent": s.agent,
            "dependsOn": [s.inputFrom] if s.inputFrom else []
        })
    return CompiledWorkflow(name=name, version=version, steps=dag)

# Note: replace with ruamel.yaml to preserve comments in real impl
def _load_yaml(path):
    import yaml
    return yaml.safe_load(pathlib.Path(path).read_text())
```

**`/api/routes/tasks_from_spec.py`**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from taskspec.compiler import compile_taskspec

router = APIRouter()

class FromSpecReq(BaseModel):
    specRef: str  # e.g., "doc_pipeline@1.0.0"
    input: dict
    tenant: str = "default"

@router.post("/tasks/from-spec")
async def create_from_spec(req: FromSpecReq):
    name, version = req.specRef.split("@", 1)
    path = f"specs/{name}.yaml"
    wf = compile_taskspec(path)
    # TODO: schedule Temporal workflow here
    return {"status": "queued", "workflow": wf.model_dump()}
```

**`/tests/test_taskspec_compiler.py`**

```python
from taskspec.compiler import compile_taskspec

def test_compile_minimal_yaml(tmp_path):
    p = tmp_path/"simple.yaml"
    p.write_text("""
apiVersion: maf/v1
kind: TaskSpec
metadata: {name: demo, version: 1.0.0}
steps:
  - {id: a, agent: doc_writer}
  - {id: b, agent: qa_tester, inputFrom: a}
""")
    wf = compile_taskspec(str(p))
    assert [s["id"] for s in wf.steps] == ["a", "b"]
```

---

### 2) Router: library, configs, tests

**`/core/router.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import random, time, hashlib, json

@dataclass
class ModelInfo:
    id: str
    priors: Dict[str, float]
    quality: str
    max_ctx: int

class Router:
    def __init__(self, models_cfg: Dict[str, Any], policies: Dict[str, Any]):
        self.models = {m["id"]: ModelInfo(
            id=m["id"], priors=m.get("priors", {}), quality=m.get("quality", "draft"), max_ctx=m.get("max_ctx", 8192)
        ) for m in models_cfg.get("models", [])}
        self.policies = policies
        self.rng = random.Random()

    def select_model(self, task_type: str, tenant: str = "default", hints: Dict[str, Any] | None = None) -> Dict[str, Any]:
        pol = self._tenant_policy(tenant)
        candidates = [m for m in self.models.values() if self._meets_quality(m, pol)]
        if not candidates:
            raise ValueError("No candidate models meet policy")
        # naive cost+latency score; replace with bandit/AB later
        def score(m: ModelInfo):
            lat = m.priors.get("latency_ms_p50", 1500)
            cin = m.priors.get("input_tok_usd", 0.0005)
            cout = m.priors.get("output_tok_usd", 0.0005)
            return lat + 100000 * (cin + cout)  # rough composite
        chosen = sorted(candidates, key=score)[0]
        rationale = {"policy": pol, "scored": [m.id for m in candidates]}
        return {"model_id": chosen.id, "rationale": rationale}

    def _tenant_policy(self, tenant: str) -> Dict[str, Any]:
        base = self.policies.get("routing", {}).get("default", {})
        over = self.policies.get("routing", {}).get("tenants", {}).get(tenant, {})
        return {**base, **over}

    def _meets_quality(self, m: ModelInfo, pol: Dict[str, Any]) -> bool:
        tiers = ["draft", "medium", "high"]
        want = pol.get("quality", "medium")
        return tiers.index(m.quality) >= tiers.index(want)

# convenience for agents
_router_singleton: Router | None = None

def init_router(models_cfg: Dict[str, Any], policies: Dict[str, Any]):
    global _router_singleton
    _router_singleton = Router(models_cfg, policies)

def select_model(task_type: str, tenant: str = "default", hints: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if _router_singleton is None:
        raise RuntimeError("Router not initialized")
    return _router_singleton.select_model(task_type, tenant, hints)
```

**`/tests/test_router.py`**

```python
from core.router import Router

MODELS = {
  "models": [
    {"id": "openai:gpt-4.1-mini", "priors": {"latency_ms_p50": 650, "input_tok_usd": 0.0003, "output_tok_usd": 0.0006}, "quality": "medium", "max_ctx": 128000},
    {"id": "openrouter:llama-3.1-70b", "priors": {"latency_ms_p50": 900, "input_tok_usd": 0.0001, "output_tok_usd": 0.0002}, "quality": "medium", "max_ctx": 32000}
  ]
}
POLICY = {"routing": {"default": {"quality": "medium"}}}

def test_pick_fastest_within_policy():
  r = Router(MODELS, POLICY)
  pick = r.select_model("doc_draft")
  assert pick["model_id"] == "openai:gpt-4.1-mini"
```

---

### 3) Tracing & Replay: lib, CLI, minimal OTel wiring

**`/core/tracing.py`**

```python
from __future__ import annotations
from contextlib import contextmanager
from time import perf_counter
import hashlib, json

class Trace:
    def __init__(self, exporter):
        self.exporter = exporter

    @contextmanager
    def span(self, name: str, **attrs):
        start = perf_counter()
        try:
            yield attrs
        finally:
            attrs["latency.ms"] = (perf_counter() - start) * 1000
            self.exporter.emit(name, attrs)

class Exporter:
    def __init__(self, sink):
        self.sink = sink  # e.g., S3/MinIO adapter
    def emit(self, name: str, attrs: dict):
        self.sink.write({"name": name, "attrs": attrs})

class MemorySink:
    def __init__(self):
        self.events = []
    def write(self, ev):
        self.events.append(ev)
```

**`/core/replay.py`**

```python
from __future__ import annotations
import json

class ReplayStore:
    def __init__(self, blob):
        self.blob = blob  # adapter with get(task_id)
    def snapshot(self, task_id: str, payload: dict):
        self.blob.put(task_id, json.dumps(payload).encode())
    def load(self, task_id: str) -> dict:
        return json.loads(self.blob.get(task_id).decode())

def replay(task_id: str, runner):
    snap = runner.store.load(task_id)
    # rehydrate minimal contract
    return runner.run(snap)

class DummyRunner:
    def __init__(self, store):
        self.store = store
    def run(self, snap: dict):
        # stub: replace with agent re-entry
        return {"status": "replayed", "task_id": snap.get("task_id")}
```

**`/cli/maf_replay.py`**

```python
import argparse
from core.replay import ReplayStore, DummyRunner, replay

class InMemoryBlob:
  def __init__(self):
    self.db = {}
  def put(self, k, v):
    self.db[k] = v
  def get(self, k):
    return self.db[k]

if __name__ == "__main__":
  p = argparse.ArgumentParser()
  p.add_argument("task_id")
  args = p.parse_args()
  store = ReplayStore(InMemoryBlob())
  runner = DummyRunner(store)
  store.snapshot(args.task_id, {"task_id": args.task_id})
  res = replay(args.task_id, runner)
  print(res)
```

**`/tests/test_replay.py`**

```python
from core.replay import ReplayStore, DummyRunner, replay

class Mem:
  def __init__(self):
    self.m = {}
  def put(self, k, v):
    self.m[k] = v
  def get(self, k):
    return self.m[k]

def test_replay_roundtrip():
  store = ReplayStore(Mem())
  runner = DummyRunner(store)
  store.snapshot("t1", {"task_id": "t1"})
  out = replay("t1", runner)
  assert out["status"] == "replayed"
```

---

# Integration Notes

1. **Wire the API**: include `api/routes/tasks_from_spec.py` in FastAPI app and add `/specs` to the image.
2. **Init Router**: at agent startup, load `config/models.yaml` and `policies/model_router.yaml`, then `init_router(...)`. Replace direct model IDs with `select_model(...)`.
3. **Tracing Hooks**: wrap agent calls with `Trace.exporter`. Persist snapshots to MinIO (or S3) via a thin adapter.

# Make Targets (optional)

**`/Makefile`**

```make
.PHONY: test rfcs
rfcs:
	@ls rfcs/*.md

test:
	pytest -q
```

# CI Hints

* Add the tests to your GitHub Actions `pytest` job.
* Lint RFC files on PR (spellcheck + front-matter check optional).

# Next Migration Candidates

* Migrate `doc_writer → compliance_checker → qa_tester` to TaskSpec first.
* Enable Router on `doc_writer` only, with a 70/30 AB.
* Turn on tracing for those three agents before expanding fleet.


Notes:

Dropped! I’ve placed three repo-ready RFCs plus minimal code scaffolds into a canvas for straight copy-paste into your tree. Paths and files are all spelled out so the team can branch and land them immediately.

Suggested merge plan:

Create /rfcs/ and commit the three RFCs.

Add the scaffolds in /specs/, /core/, /api/routes/, /cli/, and /tests/.

Wire the new FastAPI route and init the router in one agent.

Run pytest; open a PR titled “RFC-001/2/3 + scaffolds”.

From there, we can harden the compiler (Temporal wiring), swap the router’s naive score for a bandit, and bolt OTel exporters onto the tracing stub. Ready when you want the next layer (Temporal workflow glue + MinIO adapter + router experiments config).
