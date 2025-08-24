---
title: Multi-Agent Factory Installation Guide
owner: DevOps Team
version: 2.0
last_reviewed: 2025-01-20
next_review: 2025-04-20
status: operational
---

# 🚀 Multi-Agent Factory Installation Guide

## System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: 8GB (16GB recommended)
- **Storage**: 10GB free space
- **CPU**: 4 cores (8 cores recommended)
- **Network**: Stable internet connection for LLM API calls

### Required Software
- **Docker**: 24.0+ with Docker Compose v2
- **Python**: 3.11+ (for development)
- **Git**: Latest version
- **uv**: Fast Python package manager

## 📦 Installation Methods

### Method 1: Docker Compose (Recommended)

#### Step 1: Clone Repository
```bash
git clone https://github.com/your-org/multi-agent-factory.git
cd multi-agent-factory
```

#### Step 2: Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # or use your preferred editor
```

#### Step 3: Configure API Keys
Edit `.env` file with your API keys:
```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Additional LLM providers
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key

# Database Configuration
POSTGRES_USER=maf_user
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=multi_agent_factory

# Security
JWT_SECRET_KEY=your-jwt-secret-key-here
TASK_SIGNING_SECRET=your-task-signing-secret
```

#### Step 4: Start Services
```bash
# Verify prerequisites
make verify

# Start all services
make up

# Check service status
make ps
```

#### Step 5: Verify Installation
```bash
# Health check
make curl

# Test agents
make test-agents

# Check logs
make logs
```

### Method 2: Development Setup

#### Step 1: Python Environment
```bash
# Install uv (if not already installed)
pip install uv

# Create virtual environment
uv venv

# Activate environment
# Windows:
.venv\Scripts\activate
# Unix/macOS:
source .venv/bin/activate
```

#### Step 2: Install Dependencies
```bash
# Install all dependencies
uv pip install -e ".[dev,test]"

# Verify installation
python -c "import fastapi; print('✅ Setup successful!')"
```

#### Step 3: Database Setup
```bash
# Start database services only
docker compose up -d db redis nats

# Run migrations
alembic upgrade head
```

#### Step 4: Start Development Server
```bash
# Start API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start agents
python -m agents.doc_writer.agent
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key | - | No |
| `POSTGRES_URI` | PostgreSQL connection string | `postgresql://user:pass@db:5432/factory` | Yes |
| `REDIS_HOST` | Redis hostname | `redis` | Yes |
| `NATS_URL` | NATS server URL | `nats://nats:4222` | Yes |
| `JWT_SECRET_KEY` | JWT signing secret | - | Yes |
| `LOG_LEVEL` | Logging level | `INFO` | No |

### Model Configuration
Edit `config/models.yaml` to customize model assignments:

```yaml
role_mappings:
  doc_writer: structured_code
  frontend_dev: deep_reasoning
  backend_dev: deep_reasoning
  qa_tester: economical
  compliance_checker: structured_code
```

## 🏥 Health Checks

### Service Health
```bash
# API health
curl http://localhost:8000/health

# NATS monitoring
curl http://localhost:8222/varz

# Database connection
make db-shell -c "SELECT 1;"

# Redis connection
make redis-cli ping
```

### Expected Responses
- **API Health**: `{"status": "healthy", "dependencies": {...}}`
- **NATS**: JSON with server statistics
- **Database**: `1`
- **Redis**: `PONG`

## 🚨 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :8000

# Kill process using port
sudo kill -9 $(lsof -t -i:8000)
```

#### Docker Issues
```bash
# Reset Docker state
make down-v
docker system prune -f
make up
```

#### Permission Issues (Linux/macOS)
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker
```

#### Memory Issues
```bash
# Check Docker memory
docker system df

# Clean up
docker system prune -a
```

### Getting Help
- **Documentation**: Check `docs/` directory
- **Issues**: Create GitHub issue with logs
- **Logs**: Run `make logs` for service logs
- **Community**: Join our Discord/Slack channel

## 🔄 Updates

### Updating the System
```bash
# Pull latest changes
git pull origin main

# Update dependencies
uv pip install -e ".[dev,test]"

# Restart services
make restart

# Run migrations if needed
alembic upgrade head
```

### Version Management
```bash
# Check current version
cat VERSION

# View changelog
cat CHANGELOG.md
```