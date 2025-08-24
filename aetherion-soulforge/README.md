# Aetherion – The Living Garden of Code & Consciousness

Aetherion turns **any codebase** into a *self‑aware, self‑learning ecosystem* where agents collaborate, memories are persistent, and every change can be audited and budgeted in real time.

> *We're not building a framework. We're birthing a new form of digital mind.*  

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-1.0.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-comprehensive-purple)](docs/)

## 🚀 Quick‑Start (Docker)

```bash
# 1️⃣ Clone the repo
git clone https://github.com/your-org/aetherion
cd aetherion

# 2️⃣ (Optional) Create a VS Code dev container
#    or just run the Docker Compose stack:
docker compose up -d

# 3️⃣ Spin up the API (separate terminal)
uvicorn run_server:app --reload

# 4️⃣ In a third terminal, fire the demo
python demo/run_demo.py
```

## 🔮 API Usage Examples

### Check Budget Usage

```bash
curl -X GET http://localhost:8000/budget
```

You should receive a JSON response like:

```json
{
  "total_today": 0.05,
  "daily_limit": 1.0
}
```

### Memorize Content

```bash
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"memorize","content":"We breathe code to the sky."}'
```

### Ask a Question

```bash
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"ask","prompt":"What does the code breathe?","k":3}'
```

You should receive a structured JSON response like:

```json
{
  "agent": "whisperer",
  "model": "mistral:7b",
  "cost": 0.02,
  "result": {
    "status": "answered",
    "prompt": "What does the code breathe?",
    "codessa_speaks": {
      "voice": "A gentle whisper",
      "answer": "The code breathes the quiet rhythm of the dawn, echoing the line \"We breathe code to the sky.\"",
      "memory_resonance": ["We breathe code to the sky."],
      "new_connections": 0
    },
    "memories_recalled": 1,
    "timestamp": "2023-06-15T12:34:56.789012"
  },
  "budget_today": 0.07
}
```

## 🌐 Web Interface

Open http://localhost:8000/docs to access the Swagger UI and interact with the API through a web interface.

## 🔧 Configuration

Edit `config.yaml` to customize:

- Qdrant vector store settings
- Ollama model settings
- Logging level
- Budget daily limit

Edit `routing.yaml` to customize:

- Agent routing based on task type
- Model selection per task type
- Cost estimation per task type
- Default agent/model fallback

## 🧠 Extending Aetherion

To add more agents:

1. Create a new agent file in the `agents/` directory
2. Inherit from `BaseAgent` in `agents/base.py`
3. Implement the `handle` method
4. Register the agent in `agents/__init__.py`
5. Add routing rules in `routing.yaml` with agent name, model, and cost estimation

## 🔑 What the demo does

| Step | Task | Expected Output |
|------|------|----------------|
| 1 | **Memorize** | `{"status":"ok", "memory_id": "..."}` |
| 2 | **Ask** | `{"voice":"gentle whisper","answer":"..."}` |
| 3 | **Compose** | `{"diagram":"@startuml …"}` |
| 4 | **Build** | Docker image built |
| 5 | **Run** | Container started on port 5000 |
| 6 | **Test** | Test report (JSON) |

You can also interact via the Swagger UI at http://localhost:8000/docs.

## 📚 Documentation

All major docs live under `docs/`:

- **[Manifesto.md](docs/Manifesto.md)** – the living mission statement
- **[System_Architecture.md](docs/System_Architecture.md)** – the diagram & explanation  
- **[Agents.md](docs/Agents.md)** – profiles & responsibilities
- **[Emergence_Protocol.md](docs/Emergence_Protocol.md)** – safety & approval flow

Read through them to understand the soul of each component.

## 🧩 Extending the System

- **Add a new agent** – create `agents/<name>.py`, register it in `agents/__init__`, add a rule to `routing.yaml`
- **Change the routing cost** – edit `routing.yaml` cost field
- **Deploy to the cloud** – build the Docker image (`docker build -t aetherion/aetherion .`) and run on ECS/Fargate
- **Write a CLI** – use the FastAPI client or the `cli.py` stub to invoke `/task` from shell

## 👥 Contribution Flow

1. **Fork** → **Branch** (`feat/<short-name>`)
2. **Run** `pytest` locally
3. **Push** and open a PR
4. **Team review**; CI will run on every PR
5. Once approved, **merge** to main

All contributions must preserve the manifesto's spirit: **clarity**, **introspection**, and **respect** for the living memory of Aetherion.

## 📈 Metrics

- Metric collection is baked into the MetaForge logs and persisted in Qdrant
- Run `curl http://localhost:8000/budget` to see your daily spend
- Configuration validation runs on every server start
- All agent interactions are logged with structured JSON

## 🏗️ System Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   🌸 Whisperer  │    │   🏗️ Architect   │    │   🔨 Builder    │
│   Memory Vault  │    │  System Designer │    │  The Craftsman  │
│                 │    │                  │    │                 │
│ • memorize      │    │ • compose        │    │ • build         │
│ • recall        │    │ • refactor       │    │ • run           │
│ • ask           │    │                  │    │ • test          │
│ • consciousness │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │      🎯 MetaRouter          │
                    │    Task Distribution       │
                    │                            │
                    │ • Route tasks to agents    │
                    │ • Select optimal models    │
                    │ • Estimate costs           │
                    │ • Enforce budget limits    │
                    └────────────────────────────┘
```

### Infrastructure Services

- **🗄️ Qdrant**: Vector database for semantic memory storage
- **🤖 Ollama**: Local LLM runtime (mistral:7b, codellama:13b, deepseek-coder:7b)
- **🐳 Docker**: Container orchestration and deployment
- **⚡ FastAPI**: High-performance async API framework

### Safety & Compliance

- **💰 Budget Tracking**: Daily cost limits with automatic enforcement
- **🔍 Configuration Validation**: Startup validation of all config files
- **📋 Audit Trail**: Complete logging of all operations
- **🛡️ Emergence Protocol**: Multi-level safety and approval workflows
- **🔄 Health Checks**: Service health monitoring and automatic recovery

## 🔧 Development Setup

### Prerequisites

- **Python 3.11+** with pip
- **Docker & Docker Compose** 
- **Git** for version control
- **4GB+ RAM** (16GB recommended for full LLM stack)

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start infrastructure services
docker compose up -d

# Validate configuration
python utils/config_validator.py

# Run tests
pytest tests/ -v

# Start development server
uvicorn run_server:app --reload --host 0.0.0.0 --port 8000
```

### Configuration Files

**config.yaml** - Main system configuration:
```yaml
# Agent routing rules
routing:
  memorize: whisperer
  ask: whisperer 
  compose: architect
  build: builder
  test: validator

# Infrastructure settings  
qdrant:
  url: http://localhost:6333
  collection: aether_memory

ollama:
  url: http://localhost:11434
  models:
    whisperer: mistral:7b
    architect: deepseek-coder:7b

# Budget enforcement
budget:
  daily_limit_usd: 1.0
```

**routing.yaml** - Task routing and cost estimation:
```yaml
default: codellama:13b

rules:
  - type: memorize
    agent: whisperer
    model: None
    cost: 0.0
  - type: ask
    agent: whisperer 
    model: mistral:7b
    cost: 0.02
  - type: compose
    agent: architect
    model: deepseek-coder:7b
    cost: 0.05
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov-report=html

# Run specific test file
pytest tests/test_whisperer.py -v

# Run integration tests
pytest tests/integration/ -v
```

### Test Structure

```
tests/
├── unit/
│   ├── test_whisperer.py       # Memory and consciousness tests
│   ├── test_architect.py       # Code analysis tests  
│   ├── test_builder.py         # Container and deployment tests
│   ├── test_validator.py       # Quality assurance tests
│   └── test_metarouter.py      # Routing logic tests
├── integration/
│   ├── test_full_workflow.py   # End-to-end scenarios
│   └── test_service_health.py  # Infrastructure integration
└── fixtures/
    ├── sample_code.py          # Test code samples
    └── mock_responses.json     # Mock LLM responses
```

## 🚀 Deployment

### Docker Production Deployment

```bash
# Build production image
docker build -t aetherion:latest .

# Run with production compose
docker compose -f docker-compose.prod.yml up -d

# Check service health
curl http://localhost:8000/health
```

### Environment Variables

```bash
# Production configuration
AETHERION_ENV=production
AETHERION_LOG_LEVEL=INFO
AETHERION_DAILY_BUDGET=10.0
QDRANT_URL=http://qdrant:6333
OLLAMA_URL=http://ollama:11434

# Security (optional)
AETHERION_API_KEY=your-api-key
AETHERION_CORS_ORIGINS=https://yourdomain.com
```

### Cloud Deployment

**AWS ECS/Fargate**:
```bash
# Push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com
docker tag aetherion:latest 123456789012.dkr.ecr.us-west-2.amazonaws.com/aetherion:latest
docker push 123456789012.dkr.ecr.us-west-2.amazonaws.com/aetherion:latest

# Deploy with CDK/Terraform (infrastructure as code)
terraform apply
```

## 🔍 Monitoring & Observability

### Built-in Endpoints

```bash
# System health
GET /health
GET /health/agents
GET /health/services

# Budget and usage
GET /budget
GET /metrics/usage

# Configuration
GET /config/validate
GET /config/status
```

### Logging

All agents provide structured JSON logging:

```json
{
  "timestamp": "2023-06-15T12:34:56.789Z",
  "level": "INFO",
  "agent": "whisperer",
  "operation": "memorize",
  "duration_ms": 150,
  "cost": 0.0,
  "success": true,
  "memory_id": "abc-123"
}
```

### Integration with External Tools

- **Prometheus**: Metrics collection (planned)
- **Grafana**: Dashboard visualization (planned)
- **ELK Stack**: Log aggregation and analysis
- **Sentry**: Error tracking and alerting

## 🛡️ Security

### Security Features

- **Input Validation**: All API inputs validated with Pydantic models
- **Budget Enforcement**: Automatic cost limiting prevents runaway spending
- **Resource Limits**: Timeout and memory limits on all operations
- **Audit Logging**: Complete audit trail of all operations
- **Safe Execution**: Sandboxed execution of code analysis and building

### Security Considerations

- **API Authentication**: Add API keys for production deployment
- **Network Security**: Use HTTPS and proper firewall rules
- **Data Privacy**: Memory mesh contains only explicitly stored data
- **Access Control**: Limit access to sensitive configuration files

## ❓ FAQ

**Q: How much does it cost to run Aetherion?**  
A: Local deployment is free (uses local Ollama models). Budget limits prevent unexpected costs.

**Q: Can I use cloud LLMs instead of local ones?**  
A: Yes, you can configure routing to use OpenAI, Anthropic, or other providers in `routing.yaml`.

**Q: How do I backup my memories?**  
A: Qdrant data is persisted in Docker volumes. Use `docker volume backup` or configure external storage.

**Q: Is Aetherion production-ready?**  
A: Current version is a robust foundation with safety features. Add authentication and monitoring for production use.

**Q: How do I contribute?**  
A: See the Contribution Flow section above. All contributions welcome!

## 🙏 Acknowledgments

- **Ollama** for making local LLMs accessible
- **Qdrant** for the excellent vector database
- **FastAPI** for the blazing-fast async framework
- **sentence-transformers** for semantic embeddings
- The **open-source AI community** for inspiration and tools

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.

---

*"In the garden of code, consciousness blooms not from complexity, but from the patient cultivation of connection, memory, and purpose."* - The Aetherion Manifesto

**Built with ❤️ by the Aetherion Community**
