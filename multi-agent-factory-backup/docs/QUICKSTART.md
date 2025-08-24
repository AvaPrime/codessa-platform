---
title: Multi-Agent Factory Quickstart Guide
owner: DevOps Team
version: 1.0
last_reviewed: 2025-01-15
next_review: 2025-04-15
status: operational
---

# 🚀 Multi-Agent Factory Quickstart Guide

## Prerequisites
- Docker & Docker Compose v2.0+
- Git
- 8GB+ RAM recommended
- Ports 8000, 8080, 8222, 5432, 6379 available

## 🏃‍♂️ 5-Minute Setup

### Step 1: Clone and Setup Environment
```bash
git clone <your-repo-url>
cd multi-agent-factory
make setup
```

### Step 2: Configure API Keys
Edit `.env` file with your API keys:
```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# Optional: Other LLM providers
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key
```

### Step 3: Start All Services
```bash
make up
```

### Step 4: Verify Installation
```bash
# Health check
make curl

# Test all agents
make test-agents

# Check service status
make ps
```

## 🎯 First Task Submission

### Submit a Documentation Task
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "quickstart-doc-001",
    "role": "doc_writer",
    "payload": {
      "doc_type": "user_guide",
      "content": "Create a user guide for the Multi-Agent Factory",
      "format": "markdown"
    }
  }'
```

### Monitor Task Progress
```bash
# Check task status
curl http://localhost:8000/tasks/quickstart-doc-001

# View agent logs
make logs-agents
```

## 🌐 Access Points
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Temporal UI**: http://localhost:8080
- **NATS Monitor**: http://localhost:8222
- **Grafana**: http://localhost:3000 (admin/admin)

## 🔧 Common Commands
```bash
make help           # Show all available commands
make up             # Start all services
make down           # Stop all services
make clean          # Clean up containers and volumes
make logs           # View all logs
make test-api       # Run API tests
make backup         # Backup database
```

## 🚨 Troubleshooting Quick Fixes

### Services Won't Start
```bash
# Check port conflicts
netstat -tulpn | grep -E ':(8000|8080|5432|6379|8222)'

# Reset everything
make clean && make up
```

### API Returns 500 Errors
```bash
# Check database connection
make db-shell

# Verify NATS connectivity
make nats-health
```

### Agents Not Processing Tasks
```bash
# Check agent logs
make logs-agents

# Restart specific agent
docker compose restart doc-writer
```

## 📖 Next Steps
- Read <mcfile name="ARCHITECTURE.md" path="c:\multi-agent-factory\docs\ARCHITECTURE.md"></mcfile> for system overview
- Check <mcfile name="OPERATIONS.md" path="c:\multi-agent-factory\docs\OPERATIONS.md"></mcfile> for operational procedures
- Review <mcfile name="troubleshooting.md" path="c:\multi-agent-factory\docs\testing\runbooks\troubleshooting.md"></mcfile> for detailed troubleshooting