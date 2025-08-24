# Codessa ⇆ PyGPT Integration Starter Kit

This starter kit provides a complete foundation for integrating PyGPT as a desktop frontend with Codessa as the orchestration backend. It includes OpenAPI specs, mock implementation, client adapters, and deployment configurations.

## Architecture Overview

```
PyGPT Desktop UI ←→ Codessa Gateway ←→ [Model Router, KB Engine, Agent Mesh, Repo Tools]
```

**PyGPT becomes**: Thin, delightful cockpit with local UI/UX
**Codessa provides**: Heavy cognition, coordination, policy, and enterprise features

## Quick Start

1. **Boot the mock gateway**:
   ```bash
   cd mock-gateway
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload
   ```

2. **Test the endpoints**:
   ```bash
   # Health check
   curl http://localhost:8088/health

   # Create session
   curl -X POST http://localhost:8088/sessions \
     -H "Content-Type: application/json" \
     -d '{"client":"pygpt","mode":"chat+files","user":"phoenix"}'

   # Search knowledge base
   curl -X POST http://localhost:8088/kb/search \
     -H "Content-Type: application/json" \
     -d '{"q":"How does authentication work?","top_k":5}'
   ```

3. **Integrate PyGPT** (see `pygpt-adapter/` for client modifications)

## File Structure

```
├── api-spec/
│   └── codessa-gateway.yaml          # OpenAPI 3.0 specification
├── mock-gateway/
│   ├── app/
│   │   ├── main.py                   # FastAPI application
│   │   ├── models.py                 # Pydantic models
│   │   ├── routes/                   # Endpoint implementations
│   │   └── services/                 # Business logic
│   └── requirements.txt
├── pygpt-adapter/
│   ├── codessa_client.py             # PyGPT → Codessa adapter
│   └── integration_patch.py          # PyGPT modification guide
├── policies/
│   ├── repo-access.rego              # OPA repo allowlist policy
│   └── model-routing.rego            # OPA model selection policy
├── deployment/
│   ├── docker-compose.yml            # Full stack deployment
│   └── .env.example                  # Environment configuration
└── tests/
    ├── smoke-tests.sh                # Basic endpoint validation
    └── integration-tests.py          # End-to-end scenarios
```

## Core API Contracts

### Authentication & Sessions

```http
POST /auth/login
Content-Type: application/json

{
  "username": "phoenix",
  "password": "secret"
}

→ {
  "token": "eyJ...",
  "user": "phoenix",
  "expires": "2024-01-20T12:00:00Z"
}
```

```http
POST /sessions
Authorization: Bearer <token>
Content-Type: application/json

{
  "client": "pygpt",
  "mode": "chat+files",
  "caps": ["code.write", "git.push", "docs.rag"],
  "user": "phoenix",
  "ui_session_id": "<uuid>"
}

→ {
  "codessa_session_id": "<uuid>",
  "policy_token": "<jwt-like>",
  "agent_mesh": ["pm", "dev", "docs"]
}
```

### Model Router (OpenAI-compatible)

```http
POST /llm/chat-completions
Authorization: Bearer <token>
X-Session-ID: <session-id>
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [...],
  "stream": true,
  "routing_hints": {
    "cost_priority": "balanced",
    "latency_priority": "low"
  }
}

→ OpenAI-compatible response with routing metadata
```

### Knowledge Base & RAG

```http
POST /kb/ingest
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@document.pdf
metadata={"project": "Codessa", "tags": ["architecture"]}

→ {
  "doc_id": "<uuid>",
  "status": "processing",
  "chunks": 12
}
```

```http
POST /kb/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "q": "How does ACP over NATS bridge Check Runs?",
  "top_k": 6,
  "filters": {"project": "Codessa"},
  "rerank": true
}

→ {
  "hits": [
    {
      "doc_id": "...",
      "snippet": "...",
      "cite": "document.pdf:p23",
      "score": 0.89
    }
  ],
  "ctx_tokens": 2048
}
```

### Tool Registry & Execution

```http
GET /tools/list
Authorization: Bearer <token>

→ {
  "tools": [
    {
      "name": "repo.apply_patch",
      "description": "Apply code changes to repository",
      "schema": {...},
      "caps_required": ["code.write", "git.push"]
    }
  ]
}
```

```http
POST /tools/invoke
Authorization: Bearer <token>
X-Session-ID: <session-id>
Content-Type: application/json

{
  "tool": "repo.apply_patch",
  "args": {
    "repo": "github://AvaPrime/EchoPilot",
    "branch": "feat/oauth",
    "diff": "..."
  }
}

→ {
  "status": "ok",
  "commit": "abc123...",
  "checks_url": "https://github.com/.../commit/abc123.../checks"
}
```

### Agent Orchestration

```http
POST /agents/run
Authorization: Bearer <token>
X-Session-ID: <session-id>
Content-Type: application/json

{
  "type": "agent:dev",
  "intent": "add oauth to codex",
  "inputs": {
    "repo": "github://AvaPrime/EchoPilot",
    "requirements": ["OAuth 2.0", "PKCE flow", "token refresh"]
  }
}

→ {
  "run_id": "<uuid>",
  "status": "started",
  "status_url": "/agents/run/<uuid>",
  "stream_url": "/agents/run/<uuid>/stream"
}
```

```http
GET /agents/run/<run_id>/stream
Authorization: Bearer <token>
Accept: text/event-stream

→ Server-Sent Events stream:
data: {"type": "started", "agent": "pm", "message": "Analyzing requirements..."}
data: {"type": "progress", "agent": "dev", "message": "Creating OAuth service class"}
data: {"type": "completed", "outputs": {"pr_url": "...", "docs_url": "..."}}
```

## PyGPT Integration Points

### 1. Model Provider Swap

Replace PyGPT's direct provider calls:

```python
# OLD: Direct provider calls
openai.ChatCompletion.create(...)
anthropic.messages.create(...)

# NEW: Codessa gateway
codessa_client = CodessaClient(base_url="http://localhost:8088")
response = codessa_client.chat_completions(
    model="gpt-4",
    messages=messages,
    routing_hints={"cost_priority": "balanced"}
)
```

### 2. File Chat → KB Integration

```python
# OLD: Local LlamaIndex processing
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()

# NEW: Codessa KB
codessa_client.kb_ingest(files=uploaded_files)
results = codessa_client.kb_search(
    query=user_question,
    filters={"session_id": session_id}
)
```

### 3. Agent Mode Integration

```python
# NEW: Agent orchestration
if mode == "autonomous":
    run = codessa_client.agents_run(
        type="agent:dev",
        intent=user_intent,
        inputs=context
    )
    
    # Stream progress in PyGPT timeline
    for event in codessa_client.agents_stream(run.run_id):
        update_progress_ui(event)
```

## Security & Policy

### OPA Policies

**Repo Access Control** (`policies/repo-access.rego`):
```rego
package repo.access

allow {
    input.user == "phoenix"
    input.repo in data.allowed_repos[input.user]
    input.operation in ["read", "write"]
}

default allow = false
```

**Model Routing** (`policies/model-routing.rego`):
```rego
package model.routing

allow_model[model] {
    model := input.requested_model
    model in data.approved_models
    input.cost_estimate <= data.budget_limits[input.user]
}
```

### SPIFFE/mTLS

```yaml
# spiffe-config.yaml
trust_domain: "codessa.local"
node_attestor: "k8s_sat"
workload_attestors: ["k8s", "unix"]

entries:
  - spiffe_id: "spiffe://codessa.local/pygpt-gateway"
    parent_id: "spiffe://codessa.local/node"
    selectors: ["k8s:service-account:pygpt-gateway"]
```

## Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  codessa-gateway:
    build: ./mock-gateway
    ports:
      - "8088:8088"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/codessa
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
      - opa

  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: codessa
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  opa:
    image: openpolicyagent/opa:latest
    command: ["run", "--server", "/policies"]
    volumes:
      - ./policies:/policies
    ports:
      - "8181:8181"

volumes:
  postgres_data:
  redis_data:
```

### Environment Configuration

```bash
# .env
CODESSA_DATABASE_URL=postgresql://postgres:password@localhost:5432/codessa
CODESSA_REDIS_URL=redis://localhost:6379
CODESSA_OPA_URL=http://localhost:8181

# Model providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
GOOGLE_API_KEY=...

# GitHub integration
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=./github-app-key.pem
GITHUB_WEBHOOK_SECRET=...

# Observability
PROMETHEUS_PUSHGATEWAY_URL=http://localhost:9091
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

## Testing & Validation

### Smoke Tests

```bash
#!/bin/bash
# tests/smoke-tests.sh

set -e

BASE_URL="http://localhost:8088"

echo "Testing health endpoint..."
curl -f "$BASE_URL/health"

echo "Testing session creation..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/sessions" \
  -H "Content-Type: application/json" \
  -d '{"client":"pygpt","mode":"chat","user":"test"}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.codessa_session_id')
echo "Created session: $SESSION_ID"

echo "Testing KB search..."
curl -f -X POST "$BASE_URL/kb/search" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -d '{"q":"test query","top_k":5}'

echo "All smoke tests passed!"
```

### Integration Tests

```python
# tests/integration-tests.py
import pytest
import requests
from codessa_client import CodessaClient

@pytest.fixture
def client():
    return CodessaClient(base_url="http://localhost:8088")

def test_end_to_end_chat_with_files(client):
    # Create session
    session = client.create_session(
        client="pygpt",
        mode="chat+files",
        user="test"
    )
    
    # Ingest document
    with open("test-doc.pdf", "rb") as f:
        ingest_result = client.kb_ingest(
            files={"file": f},
            metadata={"test": True}
        )
    
    # Search and chat
    search_results = client.kb_search(
        q="What is the main topic?",
        session_id=session.codessa_session_id
    )
    
    chat_response = client.chat_completions(
        model="gpt-4",
        messages=[{
            "role": "user", 
            "content": f"Based on: {search_results.hits[0].snippet}, explain..."
        }],
        session_id=session.codessa_session_id
    )
    
    assert chat_response.choices[0].message.content
    assert len(search_results.hits) > 0

def test_agent_workflow(client):
    session = client.create_session(client="pygpt", mode="autonomous")
    
    run = client.agents_run(
        type="agent:dev",
        intent="create hello world API",
        inputs={"language": "python"}
    )
    
    events = list(client.agents_stream(run.run_id))
    
    assert any(e["type"] == "completed" for e in events)
    assert "outputs" in events[-1]
```

## Acceptance Criteria

✅ **Gateway Integration**: PyGPT routes all LLM calls through Codessa gateway
✅ **Session Management**: Persistent sessions with policy tokens
✅ **RAG Pipeline**: File upload → ingest → search → cite in chat
✅ **Tool Execution**: PyGPT can invoke repo operations via Codessa tools
✅ **Agent Orchestration**: Autonomous mode triggers Codessa agent workflows
✅ **Policy Enforcement**: OPA guards all capabilities with user/repo/cost limits
✅ **Observability**: All requests traced with session/user context
✅ **Security**: mTLS between services, SPIFFE identities, audit logging

## Next Steps

1. **Production Swap-ins**:
   - Replace mock with real model router (OpenAI/Anthropic/Gemini)
   - Implement pgvector-backed KB with embeddings
   - Wire GitHub App for real repo operations
   - Deploy Temporal/NATS for agent orchestration

2. **PyGPT UI Enhancements**:
   - Add "Route via Codessa" toggle in settings
   - Show live cost meters and budget remaining
   - Display citation metadata in chat bubbles
   - Agent timeline/progress view for autonomous mode

3. **Advanced Features**:
   - VS Code extension sharing session context
   - Eval-driven model routing with quality feedback
   - Cross-session memory consolidation
   - Multi-tenant deployment with org-level policies

## Support

- 📖 **API Docs**: `http://localhost:8088/docs` (Swagger UI)
- 🔍 **Health Check**: `http://localhost:8088/health`
- 📊 **Metrics**: `http://localhost:8088/metrics` (Prometheus)
- 🐛 **Debug**: Set `LOG_LEVEL=debug` for verbose logging

---

This starter kit provides everything needed to begin the PyGPT ⇆ Codessa integration. Start with the mock gateway, validate the contracts, then swap in production components as needed.