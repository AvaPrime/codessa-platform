# 🏭 Multi-Agent Factory

A **model-agnostic**, **event-driven** multi-agent system that orchestrates AI agents to collaborate on complex tasks. Built for scalability, extensibility, and production deployment.

[![CI/CD](https://github.com/your-org/multi-agent-factory/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/your-org/multi-agent-factory/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Features

- **🤖 Model Agnostic**: GPT-5, GPT-4, Claude, Gemini, Mistral, LLaMA - all supported
- **📡 Event-Driven**: NATS-based messaging for real-time agent coordination
- **🧠 Persistent Memory**: pgvector + PostgreSQL for long-term knowledge retention
- **🔐 Policy-Governed**: OPA + SPIFFE for identity and access control
- **🧱 Composable**: Add/remove agents like Lego bricks
- **⚡ Production-Ready**: Kubernetes, Docker, Terraform, CI/CD included

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                API Gateway                  │
│        REST / gRPC / WebSocket             │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│              Orchestrator                   │
│         Temporal Workflows + Routing        │
└─────────────────────┬───────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   🤖 Agent 1    🤖 Agent 2    🤖 Agent N
   (GPT-5)       (Claude)      (Local)
        │             │             │
        └─────────────┼─────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│               Event Bus (NATS)              │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│            Memory + State Layer             │
│     pgvector + Redis + PostgreSQL          │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone & Setup
```bash
git clone <your-repo-url>
cd multi-agent-factory

# Copy environment template
make setup

# Edit .env with your API keys
nano .env
```

### 2. Start Everything
```bash
# Start all services (PostgreSQL, Redis, NATS, Temporal, API)
make up

# Check if everything is running
make ps
```

### 3. Test the API
```bash
# Health check
make curl

# Submit a test task
make test-task

# List available agents
make list-agents
```

### 4. Access UIs
- **API**: http://localhost:8000
- **Temporal UI**: http://localhost:8080
- **NATS Monitoring**: http://localhost:8222

## 📋 Available Agents

| Role | Description | Default Model | Specialties |
|------|-------------|---------------|-------------|
| `doc_writer` | Technical documentation | GPT-4o | API docs, user guides, technical specs |
| `frontend_dev` | Frontend development | GPT-5 | React, Vue, Angular, TypeScript |
| `backend_dev` | Backend development | GPT-5 | Python, Node.js, databases, APIs |
| `qa_tester` | Quality assurance | GPT-4o-mini | Test plans, automation, bug reports |
| `compliance_checker` | Compliance & security | GPT-4o | Security audits, compliance checks |

## 💡 Usage Examples

### Submit a Documentation Task
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "doc-001",
    "role": "doc_writer",
    "payload": {
      "doc_type": "api",
      "content": "Create comprehensive API documentation",
      "format": "markdown"
    }
  }'
```

### Submit a Frontend Development Task
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "frontend-001", 
    "role": "frontend_dev",
    "payload": {
      "framework": "react",
      "component_type": "functional",
      "requirements": ["responsive", "dark mode", "accessibility"]
    }
  }'
```

## 🛠️ Development

### Project Structure
```
multi-agent-factory/
├── api/                    # FastAPI REST API
├── orchestrator/           # Temporal workflows & routing
│   ├── workflows/
│   └── policies/
├── agents/                 # Individual agent implementations
│   ├── doc_writer/
│   ├── frontend_dev/
│   ├── backend_dev/
│   ├── qa_tester/
│   └── compliance_checker/
├── memory/                 # Persistent storage layer
├── config/                 # Configuration files
├── infra/                  # Infrastructure as code
│   ├── docker/
│   ├── k8s/
│   └── terraform/
└── tests/                  # Test suites
```

### Commands
```bash
# Development
make up              # Start all services
make down            # Stop all services  
make logs            # View API logs
make logs-all        # View all service logs
make clean           # Clean up everything

# Database
make db-shell        # Connect to PostgreSQL
make redis-cli       # Connect to Redis

# Code Quality
make format          # Format code with black
make lint            # Lint with flake8
make test            # Run test suite

# Monitoring  
make stats           # Show Docker resource usage
```

### Adding a New Agent

1. **Create agent directory**:
```bash
mkdir agents/my_new_agent
```

2. **Implement agent class**:
```python
# agents/my_new_agent/agent.py
class MyNewAgent:
    def __init__(self, agent_id: str = "my_new_agent_001"):
        self.agent_id = agent_id
        self.role = "my_new_agent"
        self.status = "idle"
    
    async def process_task(self, payload):
        # Your agent logic here
        return "Task completed"
```

3. **Update configuration**:
```yaml
# config/models.yaml
role_mappings:
  my_new_agent: structured_code
```

4. **Register in API**:
```python
# api/main.py - add to agents list
{"role": "my_new_agent", "status": "active"}
```

## 🌐 Production Deployment

### Docker Compose (Recommended for development)
```bash
make up
```

### Kubernetes
```bash
# Apply Kubernetes manifests
kubectl apply -f infra/k8s/

# Check deployment status
kubectl get pods -n multi-agent-factory
```

### AWS with Terraform
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

## ⚙️ Configuration

### Model Profiles
Configure different model profiles in `config/models.yaml`:

```yaml
profiles:
  deep_reasoning:
    provider: openai
    model: gpt-5
    reasoning_effort: high
    max_output_tokens: 8000
    
  economical:
    provider: openai
    model: gpt-4o-mini
    temperature: 0.3
    max_output_tokens: 2000
```

### Environment Variables
Key environment variables in `.env`:

```bash
# API Keys
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here

# Database
POSTGRES_URI=postgresql://user:pass@db:5432/factory

# Services
REDIS_HOST=redis
NATS_URL=nats://nats:4222
```

## 🧪 Testing

Run the complete test suite:
```bash
make test
```

Test individual components:
```bash
pytest tests/test_agents.py -v
pytest tests/test_api.py -v
pytest tests/test_memory.py -v
```

## 📊 Monitoring & Observability

- **Temporal UI**: http://localhost:8080 - Workflow monitoring
- **NATS Monitoring**: http://localhost:8222 - Message queue stats
- **API Health**: http://localhost:8000 - Service health

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/your-org/multi-agent-factory/issues)
- 💬 [Discussions](https://github.com/your-org/multi-agent-factory/discussions)

---

**Ready to build the future of AI collaboration?** 🚀

```bash
make setup && make up
```
