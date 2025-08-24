# Staging Wiring — RAG Graph Route 10% Canary + Agent Router

This kit wires the **Memory Graph RAG route** and **Agent Router (code_dev)** into **staging** and starts a **10% canary** safely. It’s aligned with the stacks already on your canvas. Copy/paste-ready manifests, values, and a tight runbook are included.

---

## 0) Pre‑flight checklist

- [ ] Staging Prometheus + Grafana up (Horizon‑1 dashboards loaded)
- [ ] Eval service reachable from router (`EVAL_URL`)
- [ ] OPA bundle server reachable from gateway/router (`OPA_URL`)
- [ ] GitHub adapter configured for sandbox repo (test org)
- [ ] Embedding endpoint available (`EMBEDDINGS_URL`)

---

## 1) Deploy Memory Graph (staging)

**K8s manifest**: `staging/k8s/graph-deploy.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: memory-graph, namespace: staging }
spec:
  replicas: 1
  selector: { matchLabels: { app: memory-graph } }
  template:
    metadata: { labels: { app: memory-graph } }
    spec:
      containers:
        - name: api
          image: ghcr.io/yourorg/memory-graph:staging
          env:
            - { name: PG_DSN, valueFrom: { secretKeyRef: { name: pg-graph, key: dsn } } }
            - { name: EMBEDDINGS_URL, value: "http://embedder:8000/v1/embeddings" }
          ports: [ { containerPort: 8095 } ]
          readinessProbe: { httpGet: { path: /docs, port: 8095 }, initialDelaySeconds: 5 }
---
apiVersion: v1
kind: Service
metadata: { name: memory-graph, namespace: staging }
spec:
  selector: { app: memory-graph }
  ports: [ { port: 8095, targetPort: 8095 } ]
```

**Init**: run schema on the graph DB
```bash
kubectl -n staging exec -it deploy/memory-graph -- psql "$PG_DSN" -f /app/memory_graph/schema.sql
```

**Ingest job** (KB + sample repo): `staging/k8s/graph-ingest-job.yaml`
```yaml
apiVersion: batch/v1
kind: Job
metadata: { name: graph-ingest, namespace: staging }
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: ingest
          image: ghcr.io/yourorg/memory-graph:staging
          command: ["python","memory_graph/ingest.py"]
          env:
            - { name: PG_DSN, valueFrom: { secretKeyRef: { name: pg-graph, key: dsn } } }
            - { name: EMBEDDINGS_URL, value: "http://embedder:8000/v1/embeddings" }
            - { name: KB_DIR, value: "/data/kb" }
            - { name: GITHUB_TOKEN, valueFrom: { secretKeyRef: { name: github, key: token } } }
            - { name: REPO, value: "yourorg/sandbox-repo" }
          volumeMounts:
            - { name: kb, mountPath: /data/kb, readOnly: true }
      volumes:
        - name: kb
          persistentVolumeClaim: { claimName: kb-staging-pvc }
```

---

## 2) Deploy Agent Router + code_dev worker (staging)

**K8s manifest**: `staging/k8s/agent-router.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: agent-router, namespace: staging }
spec:
  replicas: 1
  selector: { matchLabels: { app: agent-router } }
  template:
    metadata: { labels: { app: agent-router } }
    spec:
      containers:
        - name: router
          image: ghcr.io/yourorg/agent-router:staging
          ports: [ { containerPort: 8096 } ]
          env:
            - { name: GITHUB_APP_URL, value: "http://github-adapter.staging.svc:8080" }
---
apiVersion: v1
kind: Service
metadata: { name: agent-router, namespace: staging }
spec:
  selector: { app: agent-router }
  ports: [ { port: 8096, targetPort: 8096 } ]
```

**OPA allow‑list** (agents): `opa/policies/agent_capabilities.rego`
```rego
package codessa.agent

default allow = false
allow {
  input.session.tenant == "sandbox"
  input.action == "git.write"
}
```

---

## 3) Router config — enable DAG stages & service URLs

**ConfigMap patch**: `staging/k8s/router-configmap-patch.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata: { name: codessa-router, namespace: staging }
data:
  GRAPH_URL: "http://memory-graph.staging.svc:8095"
  AGENT_ROUTER_URL: "http://agent-router.staging.svc:8096"
  TRACE_UI_ENABLED: "true"
```

**Route recipe update (rag)**: `router/recipes/rag.yaml` (variant with graph stage)
```yaml
version: 1
name: rag_graph_canary
pipeline:
  - id: graph_context
    with: memory_graph
    params: { contract: rag.default }
  - id: context
    with: budget
    params: { tokens: 2800 }
  - id: model
    with: auto
  - id: validate
    with: rag_default
```

**Route recipe (code)**: ensure `code.yaml` has optional `agent_call` variant for pilot
```yaml
variants:
  agent_fix:
    overrides:
      - { stage: model, with: agent_call }
```

---

## 4) Canary config — 10% for rag graph route

`/etc/canary/config.json`
```json
{
  "experiments": [
    {
      "name": "rag_graph_route",
      "enabled": true,
      "traffic": 0.10,
      "eligibility": { "domain": ["rag"], "tenant": ["sandbox"] },
      "treatments": {
        "control": { "recipe": "rag_default" },
        "canary":  { "recipe": "rag_graph_canary" }
      },
      "sticky_key": "session"
    }
  ]
}
```

**Router hook** already maps canary `recipe` to DAG selection.

---

## 5) Gateway wiring — headers & policy context

**Gateway env**
```yaml
ROUTER_URL: http://codessa-router.staging.svc
OPA_URL: http://opa.staging.svc:8181
```

**Forward graph/agent metadata**
- Ensure `metadata.routingHints.domain` is set (`rag`/`code`) from PyGPT client.
- Add `x-tenant: sandbox` for the pilot users.

---

## 6) Alerts & dashboards (staging)

**Prometheus rules**: `staging/alerts/graph-agent.rules.yaml`
```yaml
- name: graph_agent
  rules:
    - alert: RAGContractSatisfactionLow
      expr: contract_satisfied{domain="rag"} < 0.9
      for: 15m
      labels: { severity: page }
    - alert: AgentPRTimeHigh
      expr: histogram_quantile(0.5, sum(rate(agent_pr_time_seconds_bucket[15m])) by (le)) > 300
      for: 30m
      labels: { severity: warn }
```

Load Grafana seeds from the Implementation Drop (`graph.json`, `agents.json`).

---

## 7) Runbook — staging canary rollout

1) **Deploy Graph & Agent services**
```bash
kubectl -n staging apply -f staging/k8s/graph-deploy.yaml
kubectl -n staging apply -f staging/k8s/agent-router.yaml
kubectl -n staging apply -f staging/k8s/graph-ingest-job.yaml
```
2) **Patch router env & recipes; bounce pods**
```bash
kubectl -n staging apply -f staging/k8s/router-configmap-patch.yaml
kubectl -n staging rollout restart deploy/codessa-router
```
3) **Install canary config** (ConfigMap/Secret or mounted file) and restart router if file‑watch not enabled.
4) **Shadow 2h**: enable shadow mode (if available) and verify ghost routes select `rag_graph_canary` ~10%.
5) **Flip 10% canary** (already set in config) and watch dashboards:
   - **contract_satisfied** ≥ 0.9
   - **citations_from_evidence** ≥ 0.9
   - **cost_per_success** vs control (expect neutral to slight gain)
6) **Agent pilot**: run smoke on sandbox repo, confirm PR opens and TraceLens shows agent bids + provenance.
7) **Alerts armed**: ensure no pages for quality/latency; fix any policy denials.

---

## 8) Verification commands

**RAG graph smoke**
```bash
curl -sX POST http://codessa-router.staging.svc/chat-completions \
 -H 'content-type: application/json' \
 -H 'x-tenant: sandbox' \
 -d '{
  "model":"auto",
  "messages":[{"role":"user","content":"Summarize the onboarding guide"}],
  "metadata":{
    "routingHints":{"domain":"rag"},
    "contract":"rag.default",
    "query":"onboarding"
  }
}' | jq '.route,.validators,.evidence'
```

**Agent router smoke**
```bash
curl -sX POST http://agent-router.staging.svc:8096/route -H 'content-type: application/json' \
 -d '{"trace_id":"t1","domain":"code","goal":"Apply minor README fix","inputs":{"repo":"github://yourorg/sandbox-repo"},"sla_ms":300000,"policy":{}}' | jq
```

---

## 9) Rollback

- Set `traffic` to `0.0` in `rag_graph_route` and restart router.
- Switch `rag` recipe back to `rag_default` in router ConfigMap if needed.
- Scale down `memory-graph` and `agent-router` deployments.

---

## 10) Notes & guardrails

- OPA `graph_egress.rego` should block sending private graph nodes to public LLMs without waiver.
- Keep TraceLens enabled in staging; disable in prod until audit approved.
- Ingest scope: limit to last 90 days of KB/PRs for fast pilots; compact nightly.

---

This kit is minimal but production‑grade enough for a safe 10% canary. Once the KPIs hold, you can use the existing promotion gate to ramp.

