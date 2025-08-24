# Next Layer: Temporal, MinIO, and Router Experiments

## 1. Temporal Workflow Glue for TaskSpec

**Goal:** Enable compiled TaskSpecs to run as Temporal workflows with step-by-step agent invocation.

**Additions:**

* `/workflows/task_workflow.py`: Load compiled workflow, create Temporal workflow definition, each step invokes `invoke_agent` activity.
* `/activities/invoke_agent.py`: Send job to NATS, await result, enforce per-step policies.
* Modify `/api/routes/tasks_from_spec.py` to call `client.start_workflow()` instead of returning compiled DAG only.

## 2. MinIO Adapter for Tracing & Replay

**Goal:** Persist semantic traces and snapshots to MinIO/S3.

**Additions:**

* `/core/storage/minio_adapter.py`:

  ```python
  from minio import Minio
  class MinioBlob:
      def __init__(self, endpoint, access_key, secret_key, bucket):
          self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
          self.bucket = bucket
          if not self.client.bucket_exists(bucket):
              self.client.make_bucket(bucket)
      def put(self, key, data: bytes):
          self.client.put_object(self.bucket, key, io.BytesIO(data), len(data))
      def get(self, key) -> bytes:
          return self.client.get_object(self.bucket, key).read()
  ```
* Wire this adapter into `ReplayStore` and `Trace` exporters.

## 3. Router Experiments Config + Bandit

**Goal:** Route traffic between candidate models using configurable experiments.

**Additions:**

* `/core/router.py`:

  * Parse `experiments` from `model_router.yaml`.
  * Implement epsilon-greedy multi-armed bandit for variant selection.
  * Support shadow mode execution.
* `/experiments/logging.py`: Store experiment decisions and outcomes to a DB table.

## 4. Testing and CI Updates

**Tests:**

* Mock Temporal to validate DAG compilation and activity execution.
* Use MinIO Docker service in CI for blob tests.
* Simulate experiment traffic splits in router tests.

## 5. Rollout Steps

1. Deploy MinIO alongside NATS in `docker-compose.override.yml`.
2. Initialize Temporal in dev with `temporalio` Python SDK.
3. Enable TaskSpec pipelines on a single workflow for trial.
4. Enable one A/B experiment in router config.
5. Validate replay from MinIO in staging.

Once these are in, the factory will have **full deterministic orchestration, persistent replay, and intelligent routing with experiments**—ready for high-confidence scaling.

---

## Next Layer Implementation — Temporal Glue, MinIO Replay, Router Experiments, OTel (2025‑08‑14)

> This section adds concrete, drop‑in code to wire TaskSpec → Temporal workflows, persist replays to MinIO/S3, enable A/B + shadow experiments in the Router, and initialize OpenTelemetry tracing. All snippets are minimal, composable, and safe to land behind env flags.

### 0) Dependencies (add to relevant `requirements*.txt`)

```
temporalio==1.7.0
httpx==0.27.2
opentelemetry-api==1.26.0
opentelemetry-sdk==1.26.0
opentelemetry-exporter-otlp==1.26.0
boto3==1.34.162
uvloop==0.20.0; platform_system=="Linux"
tenacity==9.0.0
PyYAML==6.0.2
```

### 1) Temporal Orchestration Glue

**`/orchestration/workflows/task_workflow.py`**

```python
from __future__ import annotations
from typing import Dict, Any, List
from temporalio import workflow

@workflow.defn
class TaskWorkflow:
    @workflow.run
    async def run(self, compiled: Dict[str, Any], initial_input: Dict[str, Any], tenant: str = "default") -> Dict[str, Any]:
        ctx = {"input": initial_input, "outputs": {}, "tenant": tenant}
        for step in compiled["steps"]:
            out = await workflow.execute_activity(
                "run_step_activity",
                {
                    "step": step,
                    "input": ctx["outputs"].get(step.get("dependsOn", [None])[0]) or ctx["input"],
                    "tenant": tenant,
                },
                start_to_close_timeout=workflow.timedelta(seconds=1800),
                retry_policy=workflow.RetryPolicy(maximum_attempts=3),
            )
            ctx["outputs"][step["id"]] = out
        return {"result": ctx["outputs"].get(compiled["steps"][-1]["id"]) }
```

**`/orchestration/activities/agent_bridge.py`**

```python
from __future__ import annotations
import os, asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from temporalio import activity

API_BASE = os.getenv("MAF_API_BASE", "http://api:8000")
POLL_INTERVAL = float(os.getenv("MAF_POLL_S", "1.5"))
POLL_TIMEOUT_S = int(os.getenv("MAF_POLL_TIMEOUT_S", "900"))

@activity.defn(name="run_step_activity")
async def run_step_activity(payload: dict) -> dict:
    step = payload["step"]
    tenant = payload.get("tenant", "default")
    step_input = payload["input"]
    # Create a task via API; reuse existing publish+persist behavior
    async with httpx.AsyncClient(timeout=30) as client:
        create = await client.post(f"{API_BASE}/tasks", json={
            "agent": step["agent"],
            "input": step_input,
            "tenant": tenant,
            "metadata": {"step_id": step["id"], "workflow": "temporal"}
        })
        create.raise_for_status()
        task = create.json()
        task_id = task.get("id") or task.get("task_id")
        # Poll until done
        deadline = activity.current().info.start_to_close_deadline
        total = 0.0
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            total += POLL_INTERVAL
            r = await client.get(f"{API_BASE}/tasks/{task_id}")
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "done":
                return data.get("result") or {}
            if total > POLL_TIMEOUT_S:
                raise TimeoutError(f"Task {task_id} timed out")
```

**`/orchestration/worker.py`**

```python
from __future__ import annotations
import asyncio, os
from temporalio.client import Client
from temporalio.worker import Worker
from orchestration.workflows.task_workflow import TaskWorkflow
from orchestration.activities.agent_bridge import run_step_activity

async def main():
    target = os.getenv("TEMPORAL_TARGET", "temporal:7233")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "maf-tasks")
    client = await Client.connect(target)
    worker = Worker(client, task_queue=task_queue, workflows=[TaskWorkflow], activities=[run_step_activity])
    print(f"Temporal worker up on {target}, queue={task_queue}")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**`/orchestration/client.py`**

```python
from __future__ import annotations
import os, asyncio
from temporalio.client import Client

async def start_task_workflow(compiled: dict, initial_input: dict, tenant: str = "default") -> str:
    target = os.getenv("TEMPORAL_TARGET", "temporal:7233")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "maf-tasks")
    client = await Client.connect(target)
    handle = await client.start_workflow(
        "TaskWorkflow",
        compiled,
        initial_input,
        tenant,
        id=f"maf-{compiled['name']}-{compiled['version']}-{os.urandom(4).hex()}",
        task_queue=task_queue,
    )
    return handle.id
```

**Update `/api/routes/tasks_from_spec.py` to launch Temporal**

```python
# ... existing imports
from orchestration.client import start_task_workflow

@router.post("/tasks/from-spec")
async def create_from_spec(req: FromSpecReq):
    name, version = req.specRef.split("@", 1)
    path = f"specs/{name}.yaml"
    wf = compile_taskspec(path)
    wf_dict = wf.model_dump()
    # Kick Temporal workflow
    wid = await start_task_workflow(wf_dict, req.input, req.tenant)
    return {"status": "queued", "workflow_id": wid, "spec": wf_dict}
```

**Docker Compose additions (snippet)**

```yaml
# infra/docker/docker-compose.yml
  temporal:
    image: temporalio/auto-setup:1.26
    environment:
      - DB=sqlite
    ports: ["7233:7233"]
  worker:
    build: .
    command: python -m orchestration.worker
    depends_on: [temporal, api]
    environment:
      - TEMPORAL_TARGET=temporal:7233
      - TEMPORAL_TASK_QUEUE=maf-tasks
      - MAF_API_BASE=http://api:8000
```

### 2) MinIO/S3 Adapter for Replay Store

**`/config/storage.yaml`**

```yaml
replay:
  provider: s3
  bucket: maf-replay
  endpoint_url: http://minio:9000
  region: us-east-1
  access_key: ${MINIO_ROOT_USER}
  secret_key: ${MINIO_ROOT_PASSWORD}
```

**`/core/blob_s3.py`**

```python
from __future__ import annotations
import os, json
import boto3

class S3Blob:
    def __init__(self, bucket: str, endpoint_url: str | None = None, region: str | None = None, access_key: str | None = None, secret_key: str | None = None):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.s3.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    def put(self, key: str, data: bytes):
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="application/json")

    def get(self, key: str) -> bytes:
        obj = self.s3.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()
```

**Wire into Replay** (replace InMemoryBlob in prior scaffold)

```python
# core/replay.py
# ...
# store = ReplayStore(S3Blob(bucket, endpoint_url, region, access, secret))
```

**Docker Compose MinIO (optional)**

```yaml
  minio:
    image: minio/minio:latest
    environment:
      - MINIO_ROOT_USER=minio
      - MINIO_ROOT_PASSWORD=minio12345
    command: server /data
    ports: ["9000:9000", "9001:9001"]
```

### 3) Router: A/B and Shadow Execution

**`/core/router.py` (augment)**

```python
# ... existing imports and classes
class Router:
    # existing __init__
    def select_model(self, task_type: str, tenant: str = "default", hints: Dict[str, Any] | None = None) -> Dict[str, Any]:
        pol = self._tenant_policy(tenant)
        exp = self._pick_experiment(task_type)
        if exp:
            pick = self._route_experiment(exp)
            return {"model_id": pick["active"], "experiment": exp["name"], "shadow": pick.get("shadow"), "rationale": {"policy": pol}}
        # fallback to baseline scorer
        # ... (unchanged)

    def _pick_experiment(self, task_type: str) -> Dict[str, Any] | None:
        exps = self.policies.get("experiments", [])
        for e in exps:
            if task_type in e.get("taskTypes", []):
                return e
        return None

    def _route_experiment(self, e: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic hash on activity id would be better; simple RNG here."""
        r = self.rng.random()
        ctl = e.get("trafficSplit", {}).get("control", 0.5)
        active = e["control"] if r < ctl else e["variant"]
        shadow = e.get("shadow") and (e["variant"] if active == e["control"] else e["control"]) or None
        return {"active": active, "shadow": shadow}
```

**Agent usage with shadow call (pseudo‑LLM exec wrapper)**

```python
# agent/utils/llm_exec.py
from core.router import select_model
from core.tracing import Trace

async def run_llm(task_type: str, prompt: str, tenant: str, call_model):
    pick = select_model(task_type, tenant)
    active_id = pick["model_id"]
    out = await call_model(active_id, prompt)
    # optional shadow
    if pick.get("shadow"):
        _ = await call_model(pick["shadow"], prompt)  # ignore result; record via tracing
    return out
```

**`/tests/test_router_experiments.py`**

```python
from core.router import Router

def test_experiment_split():
    MODELS = {"models": [{"id": "a"},{"id": "b"}]}
    POL = {"routing": {"default": {"quality": "draft"}}, "experiments": [{"name": "ab", "taskTypes": ["x"], "trafficSplit": {"control": 0.0}, "control": "a", "variant": "b", "shadow": False}]}
    r = Router(MODELS, POL)
    got = r.select_model("x")
    assert got["model_id"] == "b"
```

### 4) OpenTelemetry Initialization

**`/core/otel.py`**

```python
from __future__ import annotations
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

_initialized = False

def init_tracing(service_name: str = "maf-service"):
    global _initialized
    if _initialized:
        return
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    provider.add_span_processor(processor)
    os.environ.setdefault("OTEL_SERVICE_NAME", service_name)
    _initialized = True

def get_tracer(name: str):
    return trace.get_tracer(name)
```

**Wrap FastAPI and agents** (snippet)

```python
# api/main.py or agent/__main__.py
from core.otel import init_tracing, get_tracer
init_tracing("maf-api")
tracer = get_tracer("maf.api")

# Example span
with tracer.start_as_current_span("startup"):
    pass
```

**Enrich existing semantic tracing**

```python
# core/tracing.py — when emitting, also add OTel attributes if span exists
from opentelemetry import trace
# inside exporter.emit(...):
span = trace.get_current_span()
if span and hasattr(span, "set_attribute"):
    for k,v in attrs.items():
        try:
            span.set_attribute(f"maf.{k}", v)
        except Exception:
            pass
```

**Docker Compose OTel Collector (optional minimal)**

```yaml
  otel-collector:
    image: otel/opentelemetry-collector:0.103.1
    command: ["--config=/etc/otel-collector.yaml"]
    volumes:
      - ./infra/otel/otel-collector.yaml:/etc/otel-collector.yaml
    ports: ["4318:4318"]
```

**`/infra/otel/otel-collector.yaml`**

```yaml
receivers:
  otlp:
    protocols:
      http:
exporters:
  logging: {}
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [logging]
```

### 5) CI/CD & Config Flags

* Gate Temporal-dependent tests with `pytest -m "not temporal"` until integration env exists.
* Add env toggles: `MAF_ENABLE_TEMPORAL=1`, `MAF_ENABLE_OTEL=1`.
* Store `models.yaml`, `model_router.yaml`, and `storage.yaml` in `/config/` and mount them via Docker.

### 6) E2E Smoke (manual)

1. `docker compose up -d temporal minio otel-collector api worker agents...`
2. `POST /tasks/from-spec { specRef: "doc_pipeline@1.0.0", input: {...} }`
3. Observe: worker logs (Temporal runs), API task status moves `queued→done`, replay snapshots appear in `maf-replay` bucket, traces in collector logs.

### 7) Follow-ons (short list)

* Swap DB polling for **NATS reply subjects** to reduce latency and load.
* Add **traceparent** headers in API ↔ agents for unified trace graphs.
* Replace router RNG with **sticky hashing** on task\_id to keep variants stable.

---

Layer shipped. I added Temporal workflow glue, a MinIO/S3 replay adapter, A/B + shadowing in the router, and OpenTelemetry init—clean, drop-in scaffolds with docker-compose snippets and tests. It’s all in the canvas for copy-paste.

Quick runbook:

Spin up temporal, minio, and otel-collector services via compose.

Launch the new worker service (python -m orchestration.worker).

Hit POST /tasks/from-spec and watch the workflow step through agents while the API still does the NATS publish + DB persist.

Check the maf-replay bucket for snapshots and the collector logs for traces.

Toggle experiments in /config/policies/model_router.yaml and watch the router split or shadow traffic.

When you want, we can: switch from DB polling to NATS reply subjects, add sticky hashing for experiment assignment, and wire traceparent headers so the Factory Graph shows a single end-to-end trace.