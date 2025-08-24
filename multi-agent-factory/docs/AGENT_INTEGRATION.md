---
title: Agent Integration Guide
owner: Development Team
version: 1.0
last_reviewed: 2025-01-15
next_review: 2025-04-15
status: operational
---

# 🤖 Agent Integration Guide

## Overview
This guide walks you through integrating new agents into the Multi-Agent Factory system.

## 📋 Prerequisites
- Understanding of the <mcfile name="ARCHITECTURE.md" path="c:\multi-agent-factory\docs\ARCHITECTURE.md"></mcfile>
- Python 3.11+ development environment
- Access to the codebase

## 🏗️ Step-by-Step Integration

### Step 1: Create Agent Directory Structure
```bash
mkdir agents/your_agent_name
cd agents/your_agent_name
touch agent.py requirements.txt
```

### Step 2: Implement Base Agent Interface
```python:c%3A%5Cmulti-agent-factory%5Cagents%5Cyour_agent_name%5Cagent.py
import asyncio
import logging
from typing import Dict, Any
from agents.base_agent.base_agent import BaseAgent
from config.schemas.task_message import TaskMessage
from config.schemas.result_message import ResultMessage

class YourAgentName(BaseAgent):
    def __init__(self):
        super().__init__()
        self.role = "your_agent_name"
        self.capabilities = [
            "capability_1",
            "capability_2"
        ]
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process incoming task and return result"""
        try:
            # Your agent logic here
            result = await self._execute_task(task.payload)
            
            return ResultMessage(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="completed",
                result=result,
                metadata={
                    "processing_time": self._get_processing_time(),
                    "model_used": self.model_name
                }
            )
        except Exception as e:
            logging.error(f"Task processing failed: {e}")
            return ResultMessage(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                error=str(e)
            )
    
    async def _execute_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Implement your specific task execution logic"""
        # Example implementation
        return {
            "output": "Task completed successfully",
            "artifacts": []
        }

if __name__ == "__main__":
    agent = YourAgentName()
    asyncio.run(agent.start())
```

### Step 3: Define Agent Requirements
```txt:c%3A%5Cmulti-agent-factory%5Cagents%5Cyour_agent_name%5Crequirements.txt
# Agent-specific dependencies
requests>=2.31.0
numpy>=1.24.0
# Add other dependencies as needed
```

### Step 4: Update Configuration

#### Add to models.yaml
```yaml:c%3A%5Cmulti-agent-factory%5Cconfig%5Cmodels.yaml
# ... existing code ...
your_agent_name:
  default_model: "gpt-4o"
  fallback_model: "gpt-4o-mini"
  max_tokens: 4000
  temperature: 0.7
  capabilities:
    - "capability_1"
    - "capability_2"
```

#### Update Docker Compose
```yaml:c%3A%5Cmulti-agent-factory%5Cinfra%5Cdocker%5Cdocker-compose.yml
# ... existing code ...
  your-agent-name:
    build:
      context: ../..
      dockerfile: infra/docker/agent.Dockerfile
      args:
        AGENT_ROLE: your_agent_name
    env_file:
      - ../../.env
    environment:
      - AGENT_ROLE=your_agent_name
      - AGENT_ID=your_agent_name_001
      - POSTGRES_URI=postgresql://${POSTGRES_USER:-user}:${POSTGRES_PASSWORD:-pass}@db:5432/${POSTGRES_DB:-factory}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - NATS_URL=nats://nats:4222
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      nats:
        condition: service_healthy
    volumes:
      - ../../agents:/app/agents
      - ../../memory:/app/memory
      - ../../config:/app/config
    restart: unless-stopped
```

### Step 5: Add Message Schemas
```yaml:c%3A%5Cmulti-agent-factory%5Cconfig%5Cmessage_schemas.yaml
# ... existing code ...
your_agent_name:
  input_schema:
    type: object
    properties:
      task_type:
        type: string
        enum: ["type1", "type2"]
      parameters:
        type: object
    required: ["task_type"]
  output_schema:
    type: object
    properties:
      output:
        type: string
      artifacts:
        type: array
        items:
          type: string
```

### Step 6: Create Tests
```python:c%3A%5Cmulti-agent-factory%5Ctests%5Cunit%5Ctest_your_agent_name.py
import pytest
from agents.your_agent_name.agent import YourAgentName
from config.schemas.task_message import TaskMessage

@pytest.fixture
def agent():
    return YourAgentName()

@pytest.mark.asyncio
async def test_process_task_success(agent):
    task = TaskMessage(
        task_id="test-001",
        role="your_agent_name",
        payload={
            "task_type": "type1",
            "parameters": {}
        }
    )
    
    result = await agent.process_task(task)
    assert result.status == "completed"
    assert result.task_id == "test-001"
```

### Step 7: Update Makefile
```makefile:c%3A%5Cmulti-agent-factory%5CMakefile
# ... existing code ...
test-task-your-agent: ## 🧪 Submit your agent task
	@echo "🤖 Testing Your Agent..."
	@curl -X POST http://localhost:8000/tasks \
		-H "Content-Type: application/json" \
		-d '{"task_id":"your-agent-test-'$(date +%s)'","role":"your_agent_name","payload":{"task_type":"type1","parameters":{}}}' \
		| jq '.task_id, .status' || echo "❌ Failed to submit your agent task"
```

## 🧪 Testing Your Agent

### Local Testing
```bash
# Build and start your agent
make up

# Test your agent specifically
make test-task-your-agent

# Check agent logs
docker compose logs your-agent-name
```

### Integration Testing
```bash
# Run full test suite
pytest tests/unit/test_your_agent_name.py -v

# Run integration tests
pytest tests/integration/ -k your_agent_name
```

## 📊 Monitoring and Observability

### Add Metrics
```python
# In your agent.py
from api.metrics import agent_task_counter, agent_task_duration

class YourAgentName(BaseAgent):
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        start_time = time.time()
        try:
            result = await self._execute_task(task.payload)
            agent_task_counter.labels(
                agent=self.role, 
                status="success"
            ).inc()
            return result
        except Exception as e:
            agent_task_counter.labels(
                agent=self.role, 
                status="error"
            ).inc()
            raise
        finally:
            agent_task_duration.labels(
                agent=self.role
            ).observe(time.time() - start_time)
```

### Health Checks
```python
# Add health check endpoint
async def health_check(self) -> Dict[str, Any]:
    return {
        "status": "healthy",
        "agent_id": self.agent_id,
        "role": self.role,
        "capabilities": self.capabilities,
        "last_heartbeat": datetime.utcnow().isoformat()
    }
```

## 🚀 Deployment Checklist

- [ ] Agent implements BaseAgent interface
- [ ] Requirements.txt is complete
- [ ] Configuration added to models.yaml
- [ ] Docker compose service defined
- [ ] Message schemas documented
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Metrics and monitoring configured
- [ ] Documentation updated
- [ ] Code review completed

## 🔍 Troubleshooting

### Common Issues

**Agent not receiving tasks**
- Check NATS connection
- Verify subject subscription
- Check agent registration

**Task processing failures**
- Review agent logs
- Check payload validation
- Verify model configuration

**Performance issues**
- Monitor resource usage
- Check model response times
- Review task queue depth

## 📚 Additional Resources
- <mcfile name="base_agent.py" path="c:\multi-agent-factory\agents\base_agent\base_agent.py"></mcfile>
- <mcfile name="MESSAGE_CONTRACTS.md" path="c:\multi-agent-factory\docs\MESSAGE_CONTRACTS.md"></mcfile>
- <mcfile name="troubleshooting.md" path="c:\multi-agent-factory\docs\testing\runbooks\troubleshooting.md"></mcfile>