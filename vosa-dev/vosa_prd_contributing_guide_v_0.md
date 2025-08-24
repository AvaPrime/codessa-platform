# VOSA — Product Requirements Document (PRD) & Contributing Guide v0.1

**Product:** Voice‑Orchestrated Super‑Agent (VOSA)
**Owner:** Phoenix
**Goal:** Turn conversational intent into orchestrated, parallel agent work with policy, tests, docs, and reflection built‑in.

---

## Part I — Product Requirements Document (PRD)

### 1. Problem Statement
Building modern AI systems requires juggling models, tools, infra, policy, and cost controls. Context constantly shifts across repos, docs, and services. This creates cognitive load, context switching, and slow feedback loops. Developers need a **single voice‑first interface** that plans, delegates, executes, validates, documents, and learns—so shipping becomes conversational.

### 2. Vision
“From voice instruction to reviewed pull request with docs in minutes.” VOSA acts as a Maestro that translates user intent into a deterministic plan (DAG), delegates to specialist agents in parallel, validates outcomes through a Judge/Supervisor, and records evidence, costs, and lessons into memory.

### 3. Goals (Measurable)
- **G1:** p50/p95 Voice→PR cycle ≤ 10/20 min for scoped tasks (≤150 LoC, ≤2 files, single service).
- **G2:** Realtime UX: partial STT < 300 ms; TTS start < 500 ms; barge‑in < 150 ms.
- **G3:** ≥ 60% tasks completed in **Act** mode without human edits (post v0.3), policy‑gated.
- **G4:** 100% tasks gated by tests + lint + security; zero critical vulns admitted.
- **G5:** 100% workflows traced with cost + confidence captured; dashboards for trends.
- **G6:** RAG freshness lag < 5 min from source change (repos/docs).

### 4. Non‑Goals
- Full general AGI behavior or autonomous production deployments without policy gates.
- Replacing CI/CD; VOSA orchestrates and verifies but does not supersede proven pipelines.

### 5. Target Users & Personas
- **P1 Developer (voice‑first):** Works across Python/TS. Wants to talk, get diffs/PRs + docs.
- **P2 Code Reviewer/Lead:** Wants confidence metrics, policy proofs, and crisp diffs.
- **P3 SRE/Platform:** Needs observability, rollback/compensation, cost & policy controls.
- **P4 PM/Stakeholder:** Needs progress visibility, changelogs, roadmaps, and demos.
- **P5 Security Lead:** Needs SBOMs, scan results, and policy enforcement evidence.

### 6. Key Use Cases
- **U1**: “Add `/health` to service X and document it.” → PR + docs + passing checks.
- **U2**: “Research top RAG vector stores, score them, propose migration plan.” → report + tasks.
- **U3**: “Refactor function Y; add unit tests to cover edge cases.” → patch + tests + coverage.
- **U4**: “Scan repo for secrets & critical vulns, fix or open issues with remediation.” → issues/PR.
- **U5**: “Summarize last week’s work and costs; propose next sprint.” → digest + backlog updates.

### 7. Feature Requirements
#### 7.1 Voice I/O Gateway
- Streaming STT with partials; TTS with barge‑in; device switching; transcripts persisted.
- Multi‑language STT/TTS; captions; keyboard push‑to‑talk.

#### 7.2 Maestro (Planner + Router)
- Intent → plan synthesis to DAG; decomposes into parallel tasks; mode gates (Ask/Edit/Act).
- Model router with cost/latency/accuracy priors; policy hints and budget caps.

#### 7.3 Orchestration Runtime
- Temporal‑backed workflow engine; retries, timeouts, compensation actions.
- Event bus fan‑out/gather (NATS); idempotency, replay, backpressure.

#### 7.4 Agents (MVP set)
- Code (Python/TS), Docs (MkDocs), Test (pytest/jest), Security (bandit/npm‑audit), Research (RAG + web scan).
- Each agent consumes **Task**; emits **Artifact** + telemetry; supports dry‑run.

#### 7.5 Judge/Supervisor
- Executes tests/lints/scans; computes confidence; policy gate before publish.

#### 7.6 Memory & RAG
- Project map (repos/services/deps); global RAG over repos/docs/issues.
- Artifacts ledger with hashes/provenance; preference learning hooks.

#### 7.7 Web UI
- Voice chat panel; live transcript; plan cards; task swimlanes; diff/PR preview; approvals; cost meter.
- Session playback; notifications; incident toasts; dark/light themes.

#### 7.8 Integrations
- Git providers (PRs, checks) + IDE shims (VS Code/JetBrains).
- MCP tool servers: filesystem, repo ops, cloud ops, docs ops.

#### 7.9 Observability & Finance
- OpenTelemetry traces; Langfuse/metrics dashboards; cost per step/model/workflow.

### 8. Constraints
- Zero‑trust by default (mTLS, SPIFFE identities, OPA decisions).
- Portable: local (Docker Compose) and cloud (K8s) with minimal changes.

### 9. Dependencies
- Docker, Temporal, NATS, Postgres + pgvector; STT/TTS engines; model gateway (LiteLLM/OpenRouter); LangGraph/CrewAI.

### 10. Success Metrics & KPIs
- Cycle‑time (Voice→PR), autonomy rate, test pass rate, review-to-merge time, cost per PR, confidence accuracy vs reviewer outcome, RAG freshness, incident rate.

### 11. Release Plan
- **v0.1 MVP:** Voice loop; plan→fan‑out→gather; Code/Docs agents; Judge; PR/docs publish.
- **v0.2:** Research agent; IDE shims; cost guardrails; RAG freshness < 1 min.
- **v0.3:** Cloud & Finance agents; proactive suggestions; preference learning.
- **v0.4:** Dynamic agent spawning; multi‑user collaboration; advanced policies.

### 12. Risks & Mitigations
- Latency spikes → local STT/TTS fallback; streaming partials; queue shedding.
- Hallucinations → strict acceptance tests; cross‑model critique; human gates.
- Secret exposure → redaction middleware; minimal scopes; short‑lived creds.
- Cost overrun → per‑workflow budgets; router price caps; alerts.
- Complexity creep → ADRs; feature flags; quarterly architecture review.

---

## Part II — Contributing Guide

### 1. Welcome
Thank you for helping build VOSA. This guide explains how to set up your environment, coding standards, how we review changes, and how to add new agents/tools safely.

### 2. Code of Conduct
We follow a standard Code of Conduct (Contributor Covenant). Be respectful, collaborative, and kind.

### 3. Architecture at a Glance
- **apps/ui:** Web cockpit (voice, plans, approvals)
- **apps/maestro:** FastAPI planner/router
- **apps/orchestrator:** Temporal workers (DAG execution)
- **agents/:** code, docs, test, security, research, pm, cloud, finance
- **shared/schemas:** Pydantic + TS types; versioned contracts
- **shared/clients:** Python/TS SDKs for bus/APIs
- **ops/policies:** OPA (Rego) mode gates and publish rules
- **ops/pipelines:** CI/CD workflows, SBOM, attestations

### 4. Getting Started (Local Dev)
**Prereqs:** Docker 24+, docker‑compose; Python 3.11+; Node 20+ (pnpm), Make, Git.
```bash
make up            # starts nats, postgres, maestro, orchestrator, ui
make db/seed       # seed project memory
make agents code   # start agent(s) with hot reload (repeat for docs/test/sec)
open http://localhost:3000
```

### 5. Branching & Commits
- **Branching:** feature branches from `main`: `feat/…`, `fix/…`, `chore/…`, `docs/…`.
- **Conventional Commits:** `feat: …`, `fix: …`, `docs: …`, `refactor: …`, `perf: …`, `test: …`.
- **Small PRs** preferred; each PR must be reviewable in ≤ 30 minutes.

### 6. Style & Tooling
- **Python:** ruff, black, mypy; **JS/TS:** eslint, prettier, `tsc --noEmit`.
- **Security:** bandit, npm‑audit, trivy (images), detect‑secrets.
- **Testing:** pytest/jest; contract tests for message schemas; e2e via Playwright/pytest.

### 7. Required Checks (CI)
- Lint & type check (Py+TS); unit tests; contract tests; image builds; trivy scan; e2e tests.
- Cosign signing; SBOM & provenance; PRs require green checks + 1 review.

### 8. Issue Labels & Triage
- `type:{feature,bug,docs,chore}`, `area:{voice,maestro,orchestrator,agents,ui,infra}`, `priority:{p0,p1,p2}`.
- Weekly triage: stale issues ping after 14 days; auto‑close after 45 if inactive (except `p0`).

### 9. Security Policy
- Report vulnerabilities privately to SECURITY.md contacts.
- No secrets in code or logs; use Vault/Doppler; SPIFFE/SPIRE for identities.

### 10. Release Process
- SemVer; release branches `release/x.y` → tag `vX.Y.Z`.
- GitHub Actions publish images + docs; changelog via Conventional Commits.

### 11. Docs Standards
- MkDocs Material; one task → one page with **Problem / Plan / Artifacts / Tests / Costs**.
- Diagrams via Mermaid or D2; keep diagrams under version control.

### 12. ADRs & RFCs
- **ADR:** `ops/adrs/ADR-XXXX-title.md` (decision, context, alternatives, consequences).
- **RFC:** for substantial changes; include motivation, proposal, risks, migration.

### 13. Adding a New Agent (Checklist)
1. Create agent service under `agents/<name>`; containerize with minimal image.
2. Implement **Task** consumer and **Artifact** producer; follow schemas.
3. Add dry‑run mode; unit tests for planner/edge cases; contract tests.
4. Register topics (NATS) and activities (Temporal) + retries/backoff.
5. Add OPA policies for privileges; update CODEOWNERS for review.
6. Expose MCP tool server if external access required; document endpoints.
7. Update dashboards (metrics/traces); add demo script and sample task.

### 14. Message Contracts (Essentials)
**Event Envelope**
```json
{ "id": "evt_…", "ts": "…", "session_id": "…", "actor": "…", "topic": "…", "payload": {"…": "…"}, "trace": {"workflow_id": "…", "step": "…"} }
```
**Task (Maestro→Agent)**
```json
{ "task_id": "…", "goal": "…", "context": {"repo": "…", "path": "…", "deps": ["…"], "constraints": ["…"], "mode": "edit"}, "acceptance": ["…"] }
```
**Artifact (Agent→Bus)**
```json
{ "task_id": "…", "type": "diff|doc|report|sbom|log", "uri": "…", "summary": "…", "metadata": {"…": "…"} }
```
**Review (Judge→Maestro)**
```json
{ "task_id": "…", "checks": {"tests": "pass", "lint": "pass", "sec": "warn: 0"}, "confidence": 0.85, "notes": "…" }
```

### 15. Performance Budgets
- Voice partials < 300 ms; UI interactions < 100 ms; plan synthesis p95 < 3 s.
- Orchestrator task dispatch p95 < 200 ms; artifact ingest p95 < 400 ms.

### 16. Cost Guardrails
- Per‑workflow budget; router price caps; alerts on p95 cost outliers.
- Weekly cost digest per service/agent; unit cost per successful PR.

### 17. Telemetry & Evals
- OpenTelemetry traces across UI→Maestro→Agents; Langfuse evals on critical prompts.
- Prompt/flow snapshots versioned; prompt regression tests in CI (promptfoo).

### 18. Local Development FAQ
- **STT/TTS local?** Yes—Whisper (faster‑whisper) + Piper supported.
- **Offline mode?** Enable Ollama/vLLM; disable cloud providers; keep policies on.
- **Hot reload?** Yes—uvicorn/nodemon; agents run with watchdog.

### 19. Templates
**.github/PULL_REQUEST_TEMPLATE.md**
```md
## Summary

## Checklist
- [ ] Tests added/updated
- [ ] Lint/type checks pass
- [ ] Security scans clean (no critical/high)
- [ ] Docs updated (Problem/Plan/Artifacts/Tests/Costs)
- [ ] OPA policies reviewed (if applicable)
```

**.github/ISSUE_TEMPLATE/feature_request.md**
```md
---
name: Feature request
labels: type:feature
---
## Problem
## Proposal
## Acceptance Criteria
## Risks
```

**.github/ISSUE_TEMPLATE/bug_report.md**
```md
---
name: Bug report
labels: type:bug
---
## Expected
## Observed
## Repro Steps
## Logs/Artifacts
## Impact
```

**ops/policies/examples/regression_publish.rego**
```rego
package vosa.publish

default allow = false
allow {
  input.change.confidence >= 0.8
  input.scans.vulns.critical == 0
}
```

**ops/adrs/ADR-0001-initial-architecture.md**
```md
# ADR-0001 Initial Architecture
Decision: FastAPI + Temporal + NATS + Postgres/pgvector + Web UI (WebRTC)
Context: voice-first orchestration; policy & cost guardrails
Consequences: deterministic workflows; portable local/cloud deployments
```

---

**Status:** v0.1 (draft). Submit PRs against this doc for changes.

