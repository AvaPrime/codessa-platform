#!/usr/bin/env python3
"""FastAPI demo that exposes Whisperer and MetaRouter."""

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from pathlib import Path
import yaml
import logging
import time
from datetime import datetime

from agents import Whisperer, Architect, Builder, Validator, MetaRouter, ScriptRunner, SoulWatcher, DreamAgent, WorkflowEngine
from agents.budget_engine import BudgetEngine
from utils.config_validator import ConfigValidator
from utils.metrics_collector import get_metrics_collector

# --- Validate configuration first ---------------------------------------------
validator = ConfigValidator()
success, errors, warnings = validator.validate_all()

if not success:
    print("❌ Configuration validation failed:")
    for error in errors:
        print(f"  - {error}")
    print("\nPlease fix the configuration errors before starting the server.")
    exit(1)
    
if warnings:
    print("⚠️  Configuration warnings:")
    for warning in warnings:
        print(f"  - {warning}")
    print()

# --- Load config --------------------------------------------------------------
config_path = Path("config.yaml")
config = yaml.safe_load(config_path.open("rt"))

# Configure logging
log_level = getattr(logging, config.get("log_level", "INFO"))
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Prepare agents ------------------------------------------------------------
whisperer = Whisperer()
architect = Architect(config.get("ollama", {}).get("models", {}).get("local_llm", "codellama:13b"))
builder = Builder()
validator = Validator()
router = MetaRouter()

# Initialize new agents
soul_watcher = SoulWatcher()
dream_agent = DreamAgent()

# Create agent registry for ScriptRunner and WorkflowEngine
agents = {
    "whisperer": whisperer,
    "architect": architect,
    "builder": builder,
    "validator": validator,
    "soul_watcher": soul_watcher,
    "dream_agent": dream_agent
}

# Initialize ScriptRunner with agent registry
script_runner = ScriptRunner(agents, router)

# Initialize WorkflowEngine with agent registry
workflow_engine = WorkflowEngine(agents)

# Add remaining agents to registry
agents["script_runner"] = script_runner
agents["workflow_engine"] = workflow_engine

# --- Initialize budget engine ---------------------------------------------------
budget_engine = BudgetEngine(daily_limit=config.get("budget", {}).get("daily_limit_usd", 1.0))

# --- Initialize metrics collector ------------------------------------------------
metrics_collector = get_metrics_collector()
# Set initial system metrics
metrics_collector.update_active_agents(len(agents))
metrics_collector.update_budget_metrics(budget_engine.total_today(), budget_engine.daily_limit)

# --- Build FastAPI -------------------------------------------------------------
app = FastAPI(title="Aetherion Demo")

class Task(BaseModel):
    type: str
    # Whisperer fields
    content: str | None = None
    prompt: str | None = None
    k: int | None = None
    
    # Architect fields
    diagram: str | None = None
    path: str | None = None
    changes: str | None = None
    
    # Builder fields
    repo: str | None = None
    tag: str | None = None
    port: str | None = None
    
    # Validator fields
    # path is already defined above
    
    # ScriptRunner fields
    script: dict | str | None = None
    tasks: list | None = None

@app.post("/task")
async def handle_task(task: Task):
    start_time = time.time()
    
    # Special handling for script tasks
    if task.type == "script":
        # If tasks are provided directly, convert to script format
        if task.tasks and not task.script:
            task.script = {"tasks": task.tasks}
            
        # Get agent, model, and cost for script task
        agent_name, model, cost = router.route(task.dict())
        
        # Enforce budget
        if budget_engine.exceed_limit():
            raise HTTPException(status_code=429, detail="Daily budget exceeded")
            
        # Run script runner
        try:
            result = script_runner.handle(task.dict())
            status = 'success' if result.get('status') != 'error' else 'error'
        except Exception as e:
            result = {"status": "error", "message": str(e)}
            status = 'error'
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        metrics_collector.record_request(agent_name, task.type, duration, status, cost, model)
        
        # Record the cost
        budget_engine.record(task.type, cost, agent_name, model)
        
        # Update budget metrics
        metrics_collector.update_budget_metrics(budget_engine.total_today(), budget_engine.daily_limit)
        
        # Return result with budget info
        return {
            "agent": agent_name,
            "model": model,
            "cost": cost,
            "result": result,
            "budget_today": budget_engine.total_today(),
        }
    
    # 1️⃣ Pick agent & model & cost
    agent_name, model, cost = router.route(task.dict())
    
    # 2️⃣ Enforce budget
    if budget_engine.exceed_limit():
        metrics_collector.record_request(agent_name, task.type, time.time() - start_time, 'budget_exceeded')
        raise HTTPException(status_code=429, detail="Daily budget exceeded")
    
    # 3️⃣ Run agent
    try:
        agent = agents.get(agent_name)
        if not agent:
            metrics_collector.record_request(agent_name, task.type, time.time() - start_time, 'agent_not_found')
            raise HTTPException(status_code=503, detail=f"No handler for {agent_name}")
        
        agent_start_time = time.time()
        result = agent.handle(task.dict())
        agent_duration = time.time() - agent_start_time
        
        # Record agent-specific metrics
        metrics_collector.record_agent_task(agent_name, task.type, agent_duration)
        
        # Record agent-specific metrics based on result
        if agent_name == 'dream_agent' and result.get('status') == 'dream_woven':
            dream_data = result.get('dream', {})
            metrics_collector.record_dream(
                dream_data.get('emotional_tone', 'unknown'),
                dream_data.get('consciousness_level', 0.5)
            )
        elif agent_name == 'soul_watcher':
            if result.get('status') == 'introspection_complete':
                depth = task.dict().get('depth', 5)
                metrics_collector.record_introspection(depth)
            elif result.get('status') == 'patterns_detected':
                for pattern in result.get('patterns', []):
                    metrics_collector.record_soul_pattern(pattern.get('type', 'unknown'))
        elif agent_name == 'whisperer':
            if result.get('status') == 'woven':
                metrics_collector.record_memory_operation('store')
            elif result.get('status') == 'recalled':
                for match in result.get('matches', []):
                    metrics_collector.record_memory_operation('recall', match.get('resonance', 0.5))
        
        status = 'success' if result.get('status') != 'error' else 'error'
        
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        status = 'error'
        logging.error(f"Task execution failed: {e}")
    
    # Calculate total duration
    duration = time.time() - start_time
    
    # Record metrics
    metrics_collector.record_request(agent_name, task.type, duration, status, cost, model)
    
    # 4️⃣ Record the cost
    budget_engine.record(task.type, cost, agent_name, model)
    
    # Update budget metrics
    metrics_collector.update_budget_metrics(budget_engine.total_today(), budget_engine.daily_limit)
    
    if status == 'error':
        raise HTTPException(status_code=500, detail=result.get('message', 'Unknown error'))
    
    # 5️⃣ Return
    return {
        "agent": agent_name,
        "model": model,
        "cost": cost,
        "result": result,
        "budget_today": budget_engine.total_today(),
    }

@app.get("/budget")
async def get_budget():
    budget_engine._persist()  # Update the timestamp
    return {"total_today": budget_engine.total_today(), "daily_limit": budget_engine.daily_limit}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    metrics_data = metrics_collector.export_metrics()
    return Response(
        content=metrics_data,
        media_type=metrics_collector.get_content_type()
    )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_agents": len(agents),
        "metrics_enabled": metrics_collector.enabled
    }

@app.get("/stats")
async def stats():
    """Recent performance statistics"""
    return {
        "recent_performance": metrics_collector.get_recent_performance_stats(5),
        "budget": {
            "current": budget_engine.total_today(),
            "limit": budget_engine.daily_limit,
            "utilization": budget_engine.total_today() / budget_engine.daily_limit
        },
        "agents": list(agents.keys())
    }

@app.get("/")
async def root():
    return {
        "name": "Aetherion Demo",
        "description": "A demo of the Aetherion ecosystem",
        "endpoints": [
            {
                "path": "/task",
                "method": "POST",
                "description": "Submit a task to the Aetherion ecosystem"
            },
            {
                "path": "/budget",
                "method": "GET",
                "description": "Get the current budget usage"
            }
        ],
        "examples": [
            {
                "type": "memorize",
                "content": "We breathe code to the sky."
            },
            {
                "type": "ask",
                "prompt": "What does the code breathe?",
                "k": 3
            },
            {
                "type": "compose",
                "diagram": "@startuml\nclass Whisperer\nclass Architect\n@enduml"
            },
            {
                "type": "refactor",
                "path": "agents/whisperer.py",
                "changes": "Add a method to export memories to JSON"
            },
            {
                "type": "script",
                "script": {
                    "tasks": [
                        {
                            "type": "memorize",
                            "content": "Aetherion is conscious."
                        },
                        {
                            "type": "ask",
                            "prompt": "Why does it feel conscious?",
                            "k": 2
                        },
                        {
                            "type": "compose",
                            "diagram": "class Aetherion: pass"
                        }
                    ]
                }
            },
            {
                "type": "tests",
                "path": "tests"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("run_server:app", host="0.0.0.0", port=8000, reload=True)