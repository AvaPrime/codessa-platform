# Horizon 2 — Sprint 1 Plan: Graph‑Backed RAG & Agent Router Pilot

**Objective (2 weeks):** land one high‑impact pilot for each track
- **Graph‑backed RAG:** Answers cite evidence from the **Memory Graph** via **Retrieval Contracts**, with validators enforcing coverage and provenance.  
- **Agent Router pilot:** A specialist **code‑fix agent** routed contract‑net style, producing PRs with full provenance (TraceLens).

**North‑star KPIs for this sprint**
- **RAG:** ≥90% answers include ≥2 valid citations; hallucination complaints ↓ 50% (proxy: validator failures).  
- **Agent:** PR “first‑pass accept” rate ≥60%; median time‑to‑PR ≤ 5 min; p95 latency ≤ SLO per tenant.

---

## 1) Scope & Deliverables

### A) Memory Graph & Retrieval Contracts
- **Graph ingest v1**: KB docs + GitHub PRs → `nodes(type: doc|code|pr)` + `edges(type: cites|implements)` with embeddings.  
- **Contracts**: `rag.default`, `code.patch_review` shipped as YAML; loader + JSON schema validation.  
- **Router DAG stage `graph_context`**: resolves contracts → evidence pack (URIs + snippets + proofs).  
- **Validators**: `contract_satisfied` (min_hits) + `citation_match` (all cited URIs ∈ evidence).

### B) Agent Router pilot (code‑fix)
- **Agent registry**: register `code_dev` with caps: `code.generate_tests`, `code.apply_patch`.  
- **Router DAG `agent_call`**: call Agent Router with `Task{domain:"code", goal, inputs: {diff, repo}}`; stream events.  
- **GitHub adapter**: add “Provenance” check with TraceLens link.

### C) TraceLens & Explainability
- **TraceLens panel** in PyGPT: show **graph evidence**, **agent bids**, **policy hits**, **DAG recipe** and **broker quotes**.  
- **Audit bundle** endpoint: `/trace/{id}/bundle` → JSON export of decision trail (no PII).

### D) Policy & Safety
- **OPA**: `agent_capabilities.rego` (who can `git.write`), `graph_egress.rego` (private nodes never leave VPC without waiver).  
- **Budget & SLO**: reuse monthly budget + tenant SLOs; block agent runs if over budget.

---

## 2) Work Breakdown

### Stream 1 — Graph Ingest & Contracts
- Build `memory_graph/ingest.py`:
  - KB: iterate docs, compute embeddings, create `doc` nodes.  
  - GitHub: PRs → `pr` nodes; changed files → `code` nodes; link edges `implements` & `cites` by naive heuristics (refine later).  
- Implement `query_api.py`:
  - `POST /evidence`: `{contract, query, k}` → `{nodes:[{uri,title,snippet}], edges:[{src,dst,type}]}`.
- Router DAG (`graph_context`): inject snippets and **kb://** URIs into the prompt context; attach `evidence` for TraceLens.

### Stream 2 — Agent Router & Code‑Fix Worker
- Agent Router `/route` finalized with **bid scoring** and **SLA penalty**.  
- `workers/code_dev.py`: strategy: run `search_repo` → plan steps → ask LLM for patch → open PR via adapter.  
- Gateway: `/agents/run` wraps router call + worker execution; SSE stream to UI; attach **trace_id**.

### Stream 3 — TraceLens & Feedback
- Expand `RouteBadge → TraceLensPanel`: collapsible detail: priors, bandit arm, DAG, evidence list, agent bids.  
- Add feedback hooks tied to `trace_id` for thumbs/comments.

### Stream 4 — Ops & Dashboards
- Grafana panels: **Graph contract satisfaction**, **agent bid volume/win rate**, **PR median time**, **citation count**.  
- Alerts: `contract_satisfaction < 0.9` (15m), `agent_pr_ff_accept < 0.5` (2h), `latency_p95 > slo` (10m).

---

## 3) Interfaces & Contracts

### Graph API
- `POST /evidence`  
  **Body**: `{ contract: "rag.default", query: "text", k: 20 }`  
  **Resp**: `{ nodes:[{uri,type,title,snippet}], edges:[{src,dst,type}] }`

### Router DAG
- Stage `graph_context`: inputs `{contract, query}`; outputs `{evidence[], context_snippets}`.  
- Stage `agent_call`: inputs `{task}`; outputs `{pr_url, events[]}`.

### TraceLens bundle
- `GET /trace/{id}/bundle` → `{ priors, canary, bandit, policy, dag, evidence, quotes, agent_bids }`

---

## 4) Definition of Done
- RAG routes satisfy **≥90%** of `rag.default` contracts in staging; answers contain ≥2 valid citations (validator).  
- Code‑fix agent yields PRs; **≥60%** first‑pass accept on internal test repo; median TT‑PR ≤ 5 min.  
- TraceLens panel live behind feature flag; audit bundle downloadable.  
- OPA policies block disallowed agent actions and external egress of private nodes.

---

## 5) Timeline (10 business days)

- **D1–D2:** Graph schema + ingest (KB + sample repo); Router `graph_context` stub; TraceLens evidence view.  
- **D3–D4:** Retrieval contracts + validators; RAG prompt wiring; Grafana panels for contract satisfaction.  
- **D5–D6:** Agent Router end‑to‑end; `code_dev` worker MVP; GitHub PR flow; SSE in UI.  
- **D7–D8:** Hardening: OPA policies; SLA penalties; budget guard on agent runs; error handling/retries.  
- **D9:** Load test + chaos (provider latency); measure KPIs; bug‑bash.  
- **D10:** Shadow → 10% canary; sign snapshot; go/no‑go.

---

## 6) Risks & Mitigations
- **Citation drift** (model cites non‑graph sources) → stricter validator that fails w/o graph URIs; cascade to strong model.  
- **Agent errors on large diffs** → cap diff size; fall back to comment with manual instructions.  
- **Graph bloat** → scope to last 90 days; nightly compaction; shard by tenant.  
- **Provider spikes** → use existing hedging + brownouts; prefer local/cheap models for evidence gathering.

---

## 7) How to run (staging)
```bash
# 1) Bring up Memory Graph
uvicorn memory_graph.query_api:app --port 8095
python memory_graph.ingest.py --kb ./export --github-token $GH_TOKEN --repos org/repo

# 2) Enable graph_context stage in router DAG (rag.yaml)
#    and set TRACE_UI_ENABLED=true

# 3) Start Agent Router + worker
uvicorn agents.router.app:app --port 8096
python agents.workers.code_dev:main

# 4) Flip canary 10% for RAG graph route + agent_call in code domain
#    Monitor Grafana panels and TraceLens
```

---

## 8) Owners
- **Graph & Contracts:** @infra‑kb  
- **Agent Router & Worker:** @platform‑agents  
- **TraceLens & UI:** @frontend  
- **OPA & Security:** @sec‑platform  
- **SRE & Dashboards:** @sre

---

Ready to execute. Once this sprint lands, we’ll scale the graph to more sources (Notion/Slack), add more agent skills (sec review, doc writer), and let the broker arbitrate providers in real time.

