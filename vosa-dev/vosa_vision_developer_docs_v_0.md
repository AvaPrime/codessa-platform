# VOSA Vision & Developer Docs v0.1

**Voice‑Orchestrated Super‑Agent (VOSA)**

A single, voice‑first interface that translates conversational intent into parallel, policy‑guarded agent work—plan → delegate → execute → validate → document → reflect—continuously improving with every cycle.

---

## 1) Vision
VOSA turns software creation into conversation. Speak goals; the Maestro plans tasks, routes them to specialist agents, and ships artifacts (code, docs, PRs, deployments) with tests, security checks, and human approval gates where it matters. The system learns from outcomes, cost signals, and user feedback to become faster, safer, and more precise over time.

**North Star:** From voice instruction to reviewed pull request with docs in minutes, not hours—repeatably, audibly, and visibly.

---

## 2) Objectives (measurable)
1. **Voice → PR latency (p50/p95):** ≤ 10 min / 20 min for scoped tasks (≤150 LoC, 2 files, 1 service).
2. **Realtime feel:** partial STT hypotheses < 300 ms; TTS start < 500 ms; barge‑in detection < 150 ms.
3. **Autonomy rate:** ≥ 60% of tasks completed in *Act* mode without human edits after v0.3 (with policy gates).
4. **Quality gates:** 100% tasks gated by tests + lint + security; zero critical vulns admitted.
5. **Observability:** 100% workflows traced (OpenTelemetry), with per‑task cost and confidence recorded.
6. **Knowledge freshness:** RAG index lag < 5 min from source change (repo/docs).
7. **Safety & policy:** 100% high‑impact operations require explicit allow via OPA; 0 leaked secrets in logs.

---

## 3) Directives (product principles)
- **Voice‑first, multimodal‑ready.** Audio is a first‑class input/output; text & screen augment it.
- **Human‑in‑the‑loop by design.** *Ask → Edit → Act* modes; approvals where risk or policy dictates.
- **Deterministic orchestration.** Plans materialize into explicit DAGs with retries and compensation.
- **Policy before power.** OPA governs who/what/where; SPIFFE identities; no implicit trust.
- **Cost‑aware intelligence.** Model router optimizes for price/perf; budgets enforced per workflow.
- **Evidence, not vibes.** Every claim is backed by artifacts (tests, diffs, scans, logs, SBOMs).
- **Composability via standards.** OpenAI‑compatible APIs, MCP for tools, OCI containers, OpenTelemetry.
- **Privacy pragmatic.** Local options for STT/TTS/models; zero‑copy secrets; audit everything sensitive.
- **Accessibility & inclusion.** WCAG‑AA, keyboard PTT, captions, multilingual STT/TTS.

---

## 4) System Requirements

### 4.1 Functional
1. **Voice I/O Gateway**
   - Streaming STT (partial results), TTS with barge‑in, device switching.
   - Session state (speaker, locale, mic settings). Transcript persisted.
2. **Conversation & Planning (Maestro)**
   - Intent parse → plan synthesis (DAG). Task splitting & prioritization.
   - Mode enforcement (Ask/Edit/Act). Tool/model routing with constraints.
3. **Orchestration Runtime**
   - Workflow execution (retries, timeouts, compensation). Event bus fan‑out/gather.
   - Idempotency keys; resumable runs; backpressure.
4. **Agents** (minimum set for v0.1)
   - Code (Python/TS), Docs (MkDocs), Test (pytest/jest), Security (bandit/npm‑audit), Research (docs+OSS scan).
   - Each agent consumes *Task*, emits *Artifact* + telemetry, and supports dry‑run.
5. **Judge/Supervisor**
   - Run tests/lints/scans; compute confidence; produce review notes; gate publishing.
6. **Knowledge & Memory**
   - Project map (repos, services, deps). Global RAG over repos/docs/issues.
   - Artifacts ledger with hashes/provenance; episodic memory with pinning.
7. **User Interface (Web)**
   - WebRTC voice, live transcript, plan cards, task swimlanes, diff/PR preview, approvals, cost meter.
   - Notifications & incident toasts; session playback.
8. **Integrations**
   - Git provider (PRs, checks). MCP tool access (filesystem, repo ops, cloud). IDE shims (VS Code/JetBrains).
9. **Observability & Finance**
   - Tracing (OTel), evals/feedback, metrics/dashboards. Cost tracking per step & per model.

### 4.2 Non‑Functional
- **Performance:** see Objectives #1–2; UI interactions < 100 ms for non‑audio actions.
- **Availability:** recoverable from process/node failure; workflows resume via history.
- **Security:** mTLS (Linkerd), SPIFFE identities, short‑lived creds; OPA for decisions; signed releases (SBOM/attestations).
- **Compliance:** audit logs with redaction; data retention policies; export for review.
- **Scalability:** horizontal for stateless services; work queue auto‑scales agents.
- **Maintainability:** ADRs, contracts with schema versioning, linters/formatters enforced.
- **Accessibility:** WCAG 2.2 AA adherence.

---

## 5) Architecture (concise)
- **Maestro (FastAPI):** conversation state, planning, model/tool routing.
- **Orchestrator (Temporal workers):** executes plans as DAGs; retries & rollback.
- **Event Bus (NATS):** topics for plan/task/artifact/review; backpressure & replay.
- **Memory (Postgres + pgvector):** embeddings, project graph, artifacts ledger.
- **UI (Web):** WebRTC voice, approvals, artifacts.
- **Agents (Docker):** code/docs/test/security/research/pm/cloud/finance (pluggable).
- **Policy (OPA):** gate mode transitions & high‑risk ops.
- **Observability:** OpenTelemetry → Langfuse/Grafana; cost meter.

---

## 6) MVP v0.1 Scope
- Voice loop (WebRTC, STT partials, TTS with barge‑in).
- Plan → fan‑out → gather for a single service task.
- Code + Docs agents produce a patch + MkDocs page.
- Judge runs tests, lint, basic security; computes confidence.
- UI shows plan, diffs, approvals; publish PR + docs on approve.

**Acceptance Criteria**
- Given a voice request “Add /health to service X and document it,” within 10 minutes VOSA opens a PR (diff + tests) and pushes docs to GH Pages.
- All CI checks pass; no new critical vulns; audit logs present; cost recorded.

---

## 7) Roadmap
- **v0.2:** Research agent (tools scan), IDE shims, cost guardrails, RAG freshness < 1 min.
- **v0.3:** Cloud & Finance agents, OPA fine‑grained policies, proactive suggestions.
- **v0.4:** Dynamic agent spawning, preference learning, multi‑user sessions.

---

## 8) Developer Guide

### 8.1 Repo Layout
```
/voice-super-agent
  /apps
    /ui            # Next.js/SvelteKit Web UI (voice cockpit)
    /maestro       # FastAPI planner & router
    /orchestrator  # Temporal workers (DAG execution)
  /agents
    /code /docs /test /security /research /pm /cloud /finance
  /shared
    /schemas  # Pydantic + TS types
    /clients  # Python/TS SDKs for bus & APIs
    /infra    # Helm charts, k8s, docker-compose
  /ops
    /policies  # OPA (Rego)
    /pipelines # CI/CD workflows, SBOM, attestations
```

### 8.2 Local Dev Prereqs
- Docker (24+), docker‑compose; Python 3.11+; Node 20+ with pnpm; Make; Git.

### 8.3 Quick Start (dev)
```bash
# 1) Bootstrap infra
make up        # starts nats, postgres, maestro, orchestrator, ui

# 2) Seed db & embeddings
make db/seed

# 3) Start agents (dev mode, hot reload)
make agents code docs test security

# 4) Open UI
open http://localhost:3000
```

### 8.4 Configuration (.env.example)
```
POSTGRES_URL=postgresql://postgres:dev@pg:5432/vosa
NATS_URL=nats://nats:4222
OPENAI_BASE_URL=http://gateway:4000/v1
OPENAI_API_KEY=sk‑dev
VOICE_STT_PROVIDER=whisper_local
VOICE_TTS_PROVIDER=piper
OPA_URL=http://opa:8181
```

### 8.5 Quality Gates
- Python: ruff, black, mypy; JS/TS: eslint, prettier, type‑check.
- Security: bandit, npm‑audit, trivy (images), secret‑scanner (detect‑secrets).
- Tests: unit + contract; e2e via playwright (UI) and pytest (orchestrations).
- Conventional Commits; PRs require green checks + review.

### 8.6 CI/CD (github actions)
Stages: lint → unit → build images → trivy scan → contract tests → e2e (kind) → sign (cosign) → publish.

---

## 9) API & Message Contracts

### 9.1 Event Envelope (bus)
```json
{
  "id": "evt_01H...",
  "ts": "2025-08-23T17:05:00Z",
  "session_id": "sess_...",
  "actor": "maestro|agent.code|agent.docs|judge",
  "topic": "plan.created|task.assigned|artifact.ready|review.scored",
  "payload": {"...": "domain object"},
  "trace": {"workflow_id": "wfl_...", "step": "plan->fanout->gather"}
}
```

### 9.2 Task (Maestro → Agents)
```json
{
  "task_id": "tsk_...",
  "goal": "Add health‑check endpoint to service X",
  "context": {
    "repo": "git@github.com:org/proj.git",
    "path": "services/x",
    "deps": ["fastapi", "uvicorn"],
    "constraints": ["tests must pass", "no new critical vulns"],
    "mode": "edit"
  },
  "acceptance": [
    "GET /health returns 200",
    "pytest passes",
    "bandit finds 0 high"
  ]
}
```

### 9.3 Artifact (Agents → Bus)
```json
{
  "task_id": "tsk_...",
  "type": "diff|doc|report|image|sbom|log",
  "uri": "s3://artifacts/... or file:///...",
  "summary": "Patch adds /health, updates tests",
  "metadata": {"lines": 42, "language": "python"}
}
```

### 9.4 Review / Vote (Judge → Maestro)
```json
{
  "task_id": "tsk_...",
  "checks": {
    "tests": "pass",
    "lint": "pass",
    "sec": "warn: 1 medium",
    "policy": "allow"
  },
  "confidence": 0.83,
  "notes": "Consider adding liveness to K8s manifest"
}
```

---

## 10) Policy & Modes (OPA sketches)
**Ask → Edit**
```rego
package vosa.modes

default allow = false
allow {
  input.mode_change.from == "ask"
  input.mode_change.to == "edit"
  input.user.role in {"dev", "lead"}
}
```

**Act gating for protected repos**
```rego
package vosa.publish

default allow = false
allow {
  input.repo in input.user.allowed_repos
  input.change.confidence >= 0.8
  input.scans.vulns.critical == 0
  not input.change.touching_paths[_] == "infra/prod"
}
```

---

## 11) Risks & Mitigations
- **Latency spikes:** local STT/TTS fallback; stream partials; queue shedding.
- **Hallucinations:** strict acceptance criteria, test gates, reviewer model cross‑check.
- **Secret exposure:** redaction middleware; isolated build contexts; no secrets in artifacts.
- **Cost overrun:** per‑workflow budgets, router price caps, usage alerts.
- **Complexity creep:** ADRs, kill‑switch for features, quarterly architecture review.

---

## 12) Glossary
- **Maestro:** Conversational planner & router.
- **Agent:** Specialized worker (code, docs, test…).
- **Judge:** Validator that computes confidence and gates publishing.
- **RAG:** Retrieval‑Augmented Generation over repos/docs.
- **OPA:** Open Policy Agent; policy‑as‑code engine.
- **MCP:** Model Context Protocol; standard for tool servers.

---

**Status:** v0.1 (draft). Intended for internal alignment and MVP delivery.

