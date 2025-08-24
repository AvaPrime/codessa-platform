# Codessa Gateway & IDE Wiring — End‑to‑End Tracing + PR Provenance

This stage wires the Dynamic Router into the **Codessa Gateway** and **VS Code extension**, pushes **trace IDs** through every hop, and stamps **PRs/Checks** with provenance.

> Drop‑in patches aligned with the contracts from the Starter Kit, Expansion Pack, and Router Upgrade.

---

## 0) Overview

- Gateway → Router: forwards `/llm/chat-completions` and `/route` with **B3 + Codessa headers** and **OPA pre‑checks**
- IDE Extension: shares context, issues tool invocations, and surfaces **trace badges**
- GitHub Adapter: PR body + Check Run stamped with **trace_id**, `route.model`, cost, cache/cascade flags
- SSE Streams: **Last‑Event‑ID** resume + per‑event `trace_id`

---

## 1) Gateway patches

**`/gateway/app/main.py`** (key deltas)
```python
from fastapi import FastAPI, Request, Response
import requests, uuid, time, os
from typing import Dict

ROUTER = os.getenv("ROUTER_URL", "http://router:80")
OPA = os.getenv("OPA_URL", "http://opa:8181")

app = FastAPI(title="Codessa Gateway")

# --- tracing middleware ---
@app.middleware("http")
async def trace_ctx(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
    session_id = request.headers.get("x-session-id") or request.cookies.get("codessa_session_id")
    start = time.time()
    response: Response = await call_next(request)
    dur = time.time() - start
    response.headers["x-trace-id"] = trace_id
    response.headers["server-timing"] = f"total;dur={int(dur*1000)}"
    return response

# --- OPA helper ---
import httpx
async def opa_allow(pkg: str, inp: Dict) -> bool:
    async with httpx.AsyncClient(timeout=5.0) as c:
        r = await c.post(f"{OPA}/v1/data/{pkg}/allow", json={"input": inp})
        try:
            return bool(r.json().get("result", False))
        except Exception:
            return False

# --- /llm/chat-completions → router ---
@app.post("/llm/chat-completions")
async def llm_chat(request: Request):
    body = await request.json()
    # OPA pre-check: model & budget
    allow = await opa_allow("codessa.model", {
        "user": request.headers.get("x-user-id","phoenix"),
        "model": body.get("model","auto"),
        "session": {"id": request.headers.get("x-session-id"), "scopes": (request.headers.get("x-scopes") or "").split(",")},
        "request": {"path":"/llm/chat-completions"}
    })
    if not allow:
        return Response(status_code=403, content="Model blocked by policy")

    # forward with tracing headers
    headers = {
        "content-type":"application/json",
        "x-trace-id": request.headers.get("x-trace-id") or str(uuid.uuid4()),
        "x-session-id": request.headers.get("x-session-id",""),
        "x-user-id": request.headers.get("x-user-id","phoenix"),
        "x-scopes": request.headers.get("x-scopes","")
    }
    r = requests.post(f"{ROUTER}/chat-completions", json=body, headers=headers, timeout=120)
    return Response(content=r.content, status_code=r.status_code, media_type="application/json")
```

**`/gateway/app/agents.py`** — SSE resume + trace propagation
```python
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import httpx, asyncio, uuid, os

AGENTS = os.getenv("AGENTS_URL","http://agents:80")
router = APIRouter(prefix="/agents")

@router.get("/run/{rid}/stream")
async def stream(rid: str, request: Request):
    last_id = request.headers.get("Last-Event-ID")
    trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=None) as c:
        async with c.stream("GET", f"{AGENTS}/run/{rid}/stream", headers={"x-trace-id": trace_id, "Last-Event-ID": last_id or ""}) as resp:
            async def gen():
                async for chunk in resp.aiter_raw():
                    # ensure each event carries trace_id
                    yield chunk + f"id: {trace_id}\n\n".encode()
            return StreamingResponse(gen(), media_type="text/event-stream")
```

Register this router in `main.py` and keep `/agents/run` create endpoint unchanged (just inject `x-trace-id`).

---

## 2) VS Code extension patches (trace badge + tool actions)

**`/ide-vscode/src/extension.ts`** (key excerpts)
```ts
import * as vscode from 'vscode';
import fetch from 'node-fetch';

let currentTrace: string | undefined;

function newTrace() { return (currentTrace = crypto.randomUUID()); }

async function postJSON(url: string, body: any, headers: any = {}) {
  const h = { 'content-type': 'application/json', 'x-trace-id': currentTrace ?? newTrace(), ...headers };
  const res = await fetch(url, { method: 'POST', headers: h as any, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function activate(ctx: vscode.ExtensionContext) {
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  status.text = 'Codessa: trace — n/a'; status.show();

  const share = vscode.commands.registerCommand('codessa.shareContext', async () => {
    newTrace(); status.text = `Codessa: trace — ${currentTrace?.slice(0,8)}`;
    const opened = vscode.workspace.textDocuments.map(d => d.uri.fsPath);
    await postJSON(`${process.env.CODESSA_URL}/ide/context`, { opened_files: opened }, { 'x-session-id': ctx.globalState.get('codessa_session_id') });
    vscode.window.showInformationMessage('Context shared with Codessa.');
  });

  const applyPatch = vscode.commands.registerCommand('codessa.applySuggestedPatch', async () => {
    newTrace(); status.text = `Codessa: trace — ${currentTrace?.slice(0,8)}`;
    const diff = await vscode.window.showInputBox({ prompt: 'Paste unified diff to apply' });
    if (!diff) return;
    const args = { tool: 'repo.apply_patch', args: { repo: 'github://AvaPrime/EchoPilot', diff }, session: ctx.globalState.get('codessa_session_id') };
    const res = await postJSON(`${process.env.CODESSA_URL}/tools/invoke`, args);
    vscode.window.showInformationMessage(`PR opened: #${res.pr_number}`);
  });

  ctx.subscriptions.push(share, applyPatch, status);
}
```

Add both commands to `package.json` contributes; surface a keybinding if useful.

---

## 3) GitHub Adapter — PR provenance & Check Run

**`/github_adapter/app/main.py`** (snippet around PR creation)
```python
trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
route = request.headers.get("x-route-model","unknown")
cost  = request.headers.get("x-route-cost","?")

# 4) PR
pr_body = f"""
### Codessa Provenance
- trace_id: `{trace_id}`
- route.model: `{route}`
- cost.estimated_usd: `{cost}`
- generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

<sub>Modify or remove as you wish.</sub>
"""
pr_payload = {"title": "Codessa Patch", "head": branch, "base": req.base, "body": pr_body}
pr = requests.post(f"{API}/repos/{owner}/{repo}/pulls", json=pr_payload, headers=headers).json()

# 5) Check Run (GitHub Checks API) — optional enhancement over statuses
check_payload = {
  "name": "Codessa Provenance",
  "head_sha": commit_sha,
  "status": "completed",
  "conclusion": "success",
  "output": {
    "title": "Codessa Route",
    "summary": f"trace: {trace_id}\nmodel: {route}\ncost: {cost}",
    "text": "Automated by Codessa gateway"
  }
}
requests.post(f"{API}/repos/{owner}/{repo}/check-runs", json=check_payload, headers={**headers, "Accept":"application/vnd.github+json"})
```

**Gateway → Adapter propagation**: In `/tools/invoke` when calling the adapter, set headers: `x-trace-id`, `x-route-model` (from router response), `x-route-cost` (from router response `cost.estimated_usd`).

---

## 4) Router → Gateway response enrichment

On router success:
```json
{
  "choices": [...],
  "cost": {"estimated_usd": 0.00042},
  "route": {"model":"claude-3-7","decision":"l2-learned","reason":"learned-strong","prob_strong":0.71},
  "trace_id": "..."
}
```

Gateway stores `route.model` and `cost.estimated_usd` in its request context to forward as headers to **GitHub Adapter** and other tool calls.

---

## 5) OPA tightening (examples)

_`policy/budget.rego`_
```rego
package codessa.budget

default allow = false
allow {
  input.session.budget_usd >= input.request.estimated_cost
}
```

_`policy/repo.rego`_
```rego
package codessa.repo

default allow = false
allow {
  input.session.scopes[_] == "git.write"
  startswith(input.args.repo, "github://AvaPrime/")
}
```

Apply these in the gateway before calling tools.

---

## 6) E2E test plan

1) **Trace propagation**: Run a chat via gateway; confirm `trace_id` in router response, gateway response header, and logs.
2) **IDE → PR**: Use the VS Code command `Codessa: Apply Suggested Patch` with a tiny diff. Verify PR body includes provenance and a Check Run is created.
3) **SSE resume**: Drop the network during `/agents/run/:id/stream`; verify the stream resumes with `Last-Event-ID`.
4) **OPA blocks**: Attempt `repo.apply_patch` on a disallowed repo and observe a 403 with actionable error.
5) **Grafana**: Confirm trace counters, cache hits, and cascade metrics present (from Router pack).

---

## 7) Make targets & packaging

**Gateway**
```make
run-gateway:
	uvicorn app.main:app --host 0.0.0.0 --port 8088
```

**VS Code**
```bash
# in ide-vscode/
# install vsce if needed: npm i -g @vscode/vsce
vsce package && code --install-extension codessa-bridge-0.0.1.vsix
```

---

## 8) Rollback & safety

- Keep provenance stamping behind `GITHUB_PROVENANCE_ENABLED=true` flag.
- If router is down, gateway falls back to direct provider (configurable) but **still** issues a trace ID for consistency.
- SSE streams timeboxed; auto‑retry backoff with jitter.

---

This completes the **“wire it all together”** stage: trace‑through, IDE ergonomics, and PR provenance are now first‑class citizens. Next step: canary routing + eval dashboards to optimize cost/quality continuously.

