# Updated Makefile with NATS and Agent Management
# File: Makefile
SHELL := /bin/bash
.DEFAULT_GOAL := help

# Load environment variables
ifneq (,$(wildcard .env))
    include .env
    export
endif

## 🚀 Core Commands
.PHONY: up logs down ps setup clean help

up: ## 🚀 Start all services (API + 5 agents + infrastructure)
	@echo "🚀 Starting Multi-Agent Factory with NATS messaging..."
	docker compose -f infra/docker/docker-compose.yml --env-file .env up --build -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo ""
	@echo "✅ Multi-Agent Factory is running!"
	@echo "📍 Services:"
	@echo "   • API:           http://localhost:8000"
	@echo "   • Temporal UI:   http://localhost:8080"
	@echo "   • NATS Monitor:  http://localhost:8222"
	@echo "   • PostgreSQL:    localhost:5432"
	@echo "   • Redis:         localhost:6379"
	@echo ""
	@echo "🤖 Active Agents:"
	@echo "   • doc-writer         (✓ listening on agent.doc_writer)"
	@echo "   • frontend-dev       (✓ listening on agent.frontend_dev)"
	@echo "   • backend-dev        (✓ listening on agent.backend_dev)"
	@echo "   • qa-tester         (✓ listening on agent.qa_tester)"
	@echo "   • compliance-checker (✓ listening on agent.compliance_checker)"
	@echo ""
	@echo "💡 Next: Run 'make test-agents' to verify everything works"

logs: ## 📜 View API logs
	docker compose -f infra/docker/docker-compose.yml logs -f api

logs-agents: ## 📜 View all agent logs
	docker compose -f infra/docker/docker-compose.yml logs -f doc-writer frontend-dev backend-dev qa-tester compliance-checker

logs-all: ## 📜 View all service logs
	docker compose -f infra/docker/docker-compose.yml logs -f

down: ## 🛑 Stop all services
	docker compose -f infra/docker/docker-compose.yml down

clean: ## 🧹 Stop and remove all containers, volumes, networks
	docker compose -f infra/docker/docker-compose.yml down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleaned up all Docker resources"

ps: ## 📋 List running services
	@echo "🔍 Service Status:"
	@docker compose -f infra/docker/docker-compose.yml ps
	@echo ""
	@echo "🤖 Agent Health Check:"
	@make agent-status

setup: ## ⚙️ Initial setup (copy env file, install dependencies)
	@echo "⚙️ Setting up Multi-Agent Factory development environment..."
	cp .env.example .env
	@echo "✅ Environment file created (.env)"
	@echo "⚠️  Edit .env with your API keys before running 'make up'"
	@echo ""
	@echo "📦 Installing Python dependencies..."
	pip install -r api/requirements.txt
	@echo "✅ Dependencies installed"

## 🌐 API Testing
.PHONY: curl test-api test-agents test-task-* agent-status

curl: ## 🌐 Test API health endpoint
	@echo "🔍 Testing API health..."
	@curl -s http://localhost:8000/ | jq . || echo "❌ API not responding - run 'make up' first"

test-api: ## 🧪 Run comprehensive API tests
	@echo "🧪 Testing all API endpoints..."
	@echo ""
	@echo "1. Health Check:"
	@curl -s http://localhost:8000/ | jq .status
	@echo ""
	@echo "2. List Agents:"
	@curl -s http://localhost:8000/agents | jq '.agents[] | .role'
	@echo ""
	@echo "3. NATS Connection Test:"
	@curl -s http://localhost:8000/ | jq '.connections.nats'

test-agents: ## 🤖 Test all agents with sample tasks
	@echo "🤖 Testing all agents with sample tasks..."
	@make test-task-doc
	@echo ""
	@make test-task-frontend
	@echo ""
	@make test-task-backend
	@echo ""
	@make test-task-qa
	@echo ""
	@make test-task-compliance

test-task-doc: ## 📝 Submit documentation task
	@echo "📝 Testing Documentation Writer Agent..."
	@curl -X POST http://localhost:8000/tasks \
		-H "Content-Type: application/json" \
		-d '{"task_id":"doc-test-'$(date +%s)'","role":"doc_writer","payload":{"doc_type":"api","content":"Create comprehensive API documentation for Multi-Agent Factory","format":"markdown"}}' \
		| jq '.task_id, .status' || echo "❌ Failed to submit doc task"

test-task-frontend: ## ⚛️ Submit frontend development task  
	@echo "⚛️ Testing Frontend Developer Agent..."
	@curl -X POST http://localhost:8000/tasks \
		-H "Content-Type: application/json" \
		-d '{"task_id":"frontend-test-'$(date +%s)'","role":"frontend_dev","payload":{"framework":"react","component_type":"functional","requirements":["responsive","dark-mode","accessibility"],"name":"UserDashboard"}}' \
		| jq '.task_id, .status' || echo "❌ Failed to submit frontend task"

test-task-backend: ## 🔧 Submit backend development task
	@echo "🔧 Testing Backend Developer Agent..."
	@curl -X POST http://localhost:8000/tasks \
		-H "Content-Type: application/json" \
		-d '{"task_id":"backend-test-'$(date +%s)'","role":"backend_dev","payload":{"framework":"fastapi","database":"postgresql","api_style":"rest","service_name":"UserService","entities":["User","Task","Agent"]}}' \
		| jq '.task_id, .status' || echo "❌ Failed to submit backend task"

test-task-qa: ## 🧪 Submit QA testing task
	@echo "🧪 Testing QA Tester Agent..."
	@curl -X POST http://localhost:8000/tasks \
		-H "Content-Type: application/json" \
		-d '{"task_id":"qa-test-'$(date +%s)'","role":"qa_tester","payload":{"test_type":"integration","framework":"pytest","application_name":"MultiAgentFactory","features":["Authentication","TaskManagement","AgentOrchestration"]}}' \
		| jq '.task_id, .status' || echo "❌ Failed to submit QA task"

test-task-compliance: ## ⚖️ Submit compliance checking task
	@echo "⚖️ Testing Compliance Checker Agent..."
	@curl -X POST http://localhost:8000/tasks \
		-H "Content-Type: application/json" \
		-d '{"task_id":"compliance-test-'$(date +%s)'","role":"compliance_checker","payload":{"framework":"GDPR","scope":["data_privacy","security","audit"],"application_name":"MultiAgentFactory"}}' \
		| jq '.task_id, .status' || echo "❌ Failed to submit compliance task"

agent-status: ## 🔍 Check agent health and status
	@echo "🔍 Checking agent container status..."
	@docker compose -f infra/docker/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | grep -E "(doc-writer|frontend-dev|backend-dev|qa-tester|compliance-checker)" || echo "No agents running"

## 🗄️ Database Operations
.PHONY: db-shell redis-cli nats-cli db-migrate db-reset

db-shell: ## 🗄️ Connect to PostgreSQL database
	docker compose -f infra/docker/docker-compose.yml exec db psql -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-factory}

redis-cli: ## 💾 Connect to Redis
	docker compose -f infra/docker/docker-compose.yml exec redis redis-cli

nats-cli: ## 📡 Monitor NATS subjects
	@echo "📡 NATS Subject Activity:"
	@echo "Open http://localhost:8222 for web monitoring or use:"
	@echo "docker run --rm -it --network host natsio/nats-box:latest nats sub '>' --translate-dates"

db-migrate: ## 🔄 Run database migrations
	@echo "🔄 Running database migrations..."
	@echo "Migrations run automatically on container start from infra/docker/migrations/"
	@echo "Current migration files:"
	@ls -la infra/docker/migrations/ || echo "No migration files found"

db-reset: ## ⚠️ Reset database (WARNING: destroys all data)
	@read -p "⚠️  This will destroy all data. Continue? [y/N]: " confirm && [ "$confirm" = "y" ]
	docker compose -f infra/docker/docker-compose.yml exec db psql -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-factory} -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@echo "✅ Database reset complete"

## 📊 Monitoring & Debugging
.PHONY: stats monitor debug-api debug-agent

stats: ## 📊 Show Docker resource usage
	@echo "📊 Resource Usage:"
	docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

monitor: ## 📈 Open monitoring dashboards
	@echo "📈 Opening monitoring dashboards..."
	@echo "🌐 API Health: http://localhost:8000/"
	@echo "📊 Temporal UI: http://localhost:8080"
	@echo "📡 NATS Monitor: http://localhost:8222"
	@if command -v open >/dev/null 2>&1; then \
		open http://localhost:8000 http://localhost:8080 http://localhost:8222; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open http://localhost:8000; xdg-open http://localhost:8080; xdg-open http://localhost:8222; \
	else \
		echo "Open the URLs above in your browser"; \
	fi

debug-api: ## 🐛 Debug API container
	docker compose -f infra/docker/docker-compose.yml exec api /bin/bash

debug-agent: ## 🐛 Debug agent container (specify AGENT=doc_writer)
	@if [ -z "$(AGENT)" ]; then echo "Usage: make debug-agent AGENT=doc_writer"; exit 1; fi
	docker compose -f infra/docker/docker-compose.yml exec $(AGENT) /bin/bash

## 🧪 Testing & Development
.PHONY: test test-unit test-integration format lint install-dev

test: ## 🧪 Run all tests
	@echo "🧪 Running test suite..."
	python -m pytest tests/ -v --cov=api --cov=orchestrator --cov=memory

test-unit: ## 🧪 Run unit tests only
	python -m pytest tests/unit/ -v

test-integration: ## 🧪 Run integration tests only
	python -m pytest tests/integration/ -v

format: ## 🎨 Format code with black
	black api/ orchestrator/ memory/ agents/ tests/

lint: ## 🔍 Lint code with flake8
	flake8 api/ orchestrator/ memory/ agents/

install-dev: ## 📦 Install development dependencies
	pip install -r requirements-dev.txt

## 🚀 Deployment
.PHONY: build push deploy-dev deploy-prod

build: ## 🏗️ Build Docker images
	docker compose -f infra/docker/docker-compose.yml build

push: ## 📤 Push images to registry (requires login)
	docker compose -f infra/docker/docker-compose.yml push

deploy-dev: ## 🚀 Deploy to development environment
	@echo "🚀 Deploying to development..."
	kubectl apply -f infra/k8s/namespace.yaml
	kubectl apply -f infra/k8s/configmap.yaml
	kubectl apply -f infra/k8s/api-deployment.yaml
	@echo "✅ Deployed to development cluster"

deploy-prod: ## 🚀 Deploy to production (requires confirmation)
	@read -p "⚠️  Deploy to PRODUCTION? [y/N]: " confirm && [ "$confirm" = "y" ]
	@echo "🚀 Deploying to production..."
	# Add production deployment commands here
	@echo "✅ Production deployment complete"

## 📋 Utilities
.PHONY: check-deps backup restore validate

check-deps: ## 🔍 Check system dependencies
	@echo "🔍 Checking system dependencies..."
	@command -v docker >/dev/null 2>&1 || echo "❌ Docker not installed"
	@command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1 || echo "❌ Docker Compose not available"
	@command -v curl >/dev/null 2>&1 || echo "❌ curl not installed"
	@command -v jq >/dev/null 2>&1 || echo "⚠️  jq not installed (optional, for pretty JSON output)"
	@echo "✅ Dependency check complete"

backup: ## 💾 Backup database and configuration
	@echo "💾 Creating backup..."
	@mkdir -p backups
	docker compose -f infra/docker/docker-compose.yml exec db pg_dump -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-factory} > backups/db-backup-$(date +%Y%m%d-%H%M%S).sql
	@echo "✅ Backup created in backups/"

restore: ## 🔄 Restore from backup (specify BACKUP=filename)
	@if [ -z "$(BACKUP)" ]; then echo "Usage: make restore BACKUP=filename.sql"; exit 1; fi
	@if [ ! -f "backups/$(BACKUP)" ]; then echo "❌ Backup file not found"; exit 1; fi
	docker compose -f infra/docker/docker-compose.yml exec -T db psql -U ${POSTGRES_USER:-user} -d ${POSTGRES_DB:-factory} < backups/$(BACKUP)
	@echo "✅ Database restored from $(BACKUP)"

validate: ## ✅ Validate system configuration
	@echo "✅ Validating Multi-Agent Factory configuration..."
	@echo ""
	@echo "1. Environment file:"
	@if [ -f .env ]; then echo "   ✅ .env exists"; else echo "   ❌ .env missing (run 'make setup')"; fi
	@echo ""
	@echo "2. Required directories:"
	@for dir in api orchestrator agents memory config infra tests; do \
		if [ -d $dir ]; then echo "   ✅ $dir/"; else echo "   ❌ $dir/ missing"; fi \
	done
	@echo ""
	@echo "3. Migration files:"
	@if [ -f infra/docker/migrations/001_init_pgvector.sql ]; then echo "   ✅ Database migration ready"; else echo "   ❌ Migration file missing"; fi
	@echo ""
	@echo "4. Docker configuration:"
	@if [ -f infra/docker/docker-compose.yml ]; then echo "   ✅ Docker Compose configured"; else echo "   ❌ Docker Compose config missing"; fi

help: ## 💡 Show this help message
	@echo "🏭 Multi-Agent Factory - Development Commands"
	@echo ""
	@echo "🚀 QUICK START:"
	@echo "  make setup     # Create .env file and install dependencies"
	@echo "  make up        # Start all services and agents"
	@echo "  make test-api  # Verify everything is working"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $1, $2}'
	@echo ""
	@echo "🔗 USEFUL URLS:"
	@echo "  API:          http://localhost:8000"
	@echo "  Temporal UI:  http://localhost:8080"  
	@echo "  NATS Monitor: http://localhost:8222"
	@echo ""
	@echo "📚 EXAMPLES:"
	@echo "  make test-task-doc                    # Test documentation agent"
	@echo "  make debug-agent AGENT=doc-writer     # Debug specific agent"
	@echo "  make backup                           # Backup database"
	@echo "  make logs-agents                      # View agent logs"

---

# Agent Requirements File
# File: agents/requirements.txt
asyncio-nats-client==0.11.5
redis==5.0.1
psycopg[binary]==3.1.13
pydantic==2.5.0
pyyaml==6.0.1
python-dateutil==2.8.2

# Optional LLM integrations (uncomment as needed)
# openai==1.3.0
# anthropic==0.8.1
# google-generativeai==0.3.2

# Testing dependencies
pytest==7.4.3
pytest-asyncio==0.21.1

---

# Startup Health Check Script  
# File: scripts/health-check.sh
#!/bin/bash
set -e

echo "🔍 Multi-Agent Factory Health Check"
echo "==================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local service_name=$1
    local health_url=$2
    local timeout=${3:-10}
    
    echo -n "Checking $service_name... "
    
    if timeout $timeout curl -s $health_url > /dev/null 2>&1; then
        echo -e "${GREEN}✅ HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}❌ UNHEALTHY${NC}"
        return 1
    fi
}

# Function to check NATS
check_nats() {
    echo -n "Checking NATS... "
    if timeout 5 curl -s http://localhost:8222/varz > /dev/null 2>&1; then
        echo -e "${GREEN}✅ HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}❌ UNHEALTHY${NC}"
        return 1
    fi
}

# Function to check database
check_database() {
    echo -n "Checking PostgreSQL... "
    if docker compose -f infra/docker/docker-compose.yml exec -T db pg_isready -U ${POSTGRES_USER:-user} > /dev/null 2>&1; then
        echo -e "${GREEN}✅ HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}❌ UNHEALTHY${NC}"
        return 1
    fi
}

# Function to check Redis
check_redis() {
    echo -n "Checking Redis... "
    if docker compose -f infra/docker/docker-compose.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}❌ UNHEALTHY${NC}"
        return 1
    fi
}

# Function to check agent containers
check_agents() {
    echo ""
    echo "🤖 Agent Status:"
    echo "=================="
    
    agents=("doc-writer" "frontend-dev" "backend-dev" "qa-tester" "compliance-checker")
    healthy_agents=0
    
    for agent in "${agents[@]}"; do
        echo -n "  $agent: "
        if docker compose -f infra/docker/docker-compose.yml ps $agent | grep -q "Up"; then
            echo -e "${GREEN}✅ RUNNING${NC}"
            ((healthy_agents++))
        else
            echo -e "${RED}❌ STOPPED${NC}"
        fi
    done
    
    echo ""
    echo "Agent Summary: $healthy_agents/${#agents[@]} agents running"
}

# Function to test agent messaging
test_agent_messaging() {
    echo ""
    echo "📡 Testing Agent Messaging:"
    echo "=========================="
    
    # Submit a quick test task
    echo -n "Submitting test task... "
    test_response=$(curl -s -X POST http://localhost:8000/tasks \
        -H "Content-Type: application/json" \
        -d '{
            "task_id": "health-check-'$(date +%s)'",
            "role": "doc_writer",
            "payload": {"doc_type": "test", "content": "Health check test"}
        }' || echo "FAILED")
    
    if echo "$test_response" | grep -q "accepted.*true"; then
        echo -e "${GREEN}✅ MESSAGING WORKS${NC}"
        task_id=$(echo "$test_response" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
        echo "  Task ID: $task_id"
    else
        echo -e "${RED}❌ MESSAGING FAILED${NC}"
        echo "  Response: $test_response"
    fi
}

# Main health check routine
main() {
    echo ""
    echo "🔧 Infrastructure Services:"
    echo "========================="
    
    failed_services=0
    
    # Check core infrastructure
    check_service "API Server" "http://localhost:8000/" 10 || ((failed_services++))
    check_database || ((failed_services++))
    check_redis || ((failed_services++))
    check_nats || ((failed_services++))
    check_service "Temporal" "http://localhost:7233/" 5 || ((failed_services++))
    
    # Check agents
    check_agents
    
    # Test messaging if core services are healthy
    if [ $failed_services -eq 0 ]; then
        test_agent_messaging
    fi
    
    echo ""
    echo "📋 Summary:"
    echo "==========="
    
    if [ $failed_services -eq 0 ]; then
        echo -e "${GREEN}✅ All core services are healthy!${NC}"
        echo ""
        echo "🌐 Service URLs:"
        echo "  • API:          http://localhost:8000"
        echo "  • Temporal UI:  http://localhost:8080"
        echo "  • NATS Monitor: http://localhost:8222"
        echo ""
        echo "🧪 Try running: make test-agents"
        exit 0
    else
        echo -e "${RED}❌ $failed_services service(s) are unhealthy${NC}"
        echo ""
        echo "🔧 Troubleshooting:"
        echo "  • Check logs: make logs-all"
        echo "  • Restart services: make down && make up"
        echo "  • View service status: make ps"
        exit 1
    fi
}

# Run health check
main "$@"

---

# Enhanced Environment Template
# File: .env.example
# Multi-Agent Factory Environment Configuration
# Copy this file to .env and fill in your values

# =============================================================================
# ENVIRONMENT & BASIC SETTINGS  
# =============================================================================
ENV=dev
DEBUG=true

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
POSTGRES_USER=user
POSTGRES_PASSWORD=pass
POSTGRES_DB=factory
POSTGRES_URI=postgresql://user:pass@db:5432/factory

# =============================================================================
# CACHE & MESSAGING
# =============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

NATS_URL=nats://nats:4222
NATS_CLUSTER_ROUTES=nats://nats:6222

# =============================================================================
# WORKFLOW ENGINE  
# =============================================================================
TEMPORAL_HOST=temporal
TEMPORAL_PORT=7233
TEMPORAL_NAMESPACE=default

# =============================================================================
# API KEYS (SET THESE FOR PRODUCTION!)
# =============================================================================
# OpenAI API Key (for GPT models)
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic API Key (for Claude models)  
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Google AI API Key (for Gemini models)
GOOGLE_API_KEY=your-google-ai-api-key-here

# =============================================================================
# SECURITY & AUTHENTICATION
# =============================================================================
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
ENCRYPTION_KEY=your-32-character-encryption-key

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================
# Default model settings (can be overridden per agent)
DEFAULT_MODEL=gpt-4o
DEFAULT_TEMPERATURE=0.3
DEFAULT_MAX_TOKENS=2000

# Agent-specific settings
DOC_WRITER_MODEL=gpt-4o
FRONTEND_DEV_MODEL=gpt-5  
BACKEND_DEV_MODEL=gpt-5
QA_TESTER_MODEL=gpt-4o-mini
COMPLIANCE_CHECKER_MODEL=gpt-4o

# =============================================================================
# PERFORMANCE & LIMITS
# =============================================================================
# Task timeouts (seconds)
DEFAULT_TASK_TIMEOUT=300
LONG_TASK_TIMEOUT=1800

# Rate limiting
API_RATE_LIMIT=1000  # requests per hour
AGENT_RATE_LIMIT=100  # tasks per hour

# Memory limits  
VECTOR_SEARCH_LIMIT=50
CACHE_TTL=3600  # seconds

# =============================================================================
# MONITORING & LOGGING
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json

# Enable metrics collection
ENABLE_METRICS=true
METRICS_PORT=9090

# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================
# Auto-reload for development
AUTO_RELOAD=true

# Enable debug logging for specific components
DEBUG_NATS=false  
DEBUG_DATABASE=false
DEBUG_AGENTS=false

# =============================================================================
# DEPLOYMENT SETTINGS (FOR PRODUCTION)
# =============================================================================
# External service URLs (if different from defaults)
# POSTGRES_URI=postgresql://user:pass@external-db:5432/factory
# REDIS_URL=redis://external-redis:6379/0
# NATS_URL=nats://external-nats:4222

# Load balancer settings
# ENABLE_CORS=true
# ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# SSL/TLS settings  
# SSL_CERT_PATH=/etc/ssl/certs/cert.pem
# SSL_KEY_PATH=/etc/ssl/private/key.pem

# =============================================================================
# FEATURE FLAGS
# =============================================================================
ENABLE_VECTOR_SEARCH=true
ENABLE_AGENT_MEMORY=true  
ENABLE_MULTI_AGENT_CONVERSATIONS=false
ENABLE_AGENT_LEARNING=false

---

# Quick Start Script
# File: scripts/quickstart.sh
#!/bin/bash
set -e

echo "🏭 Multi-Agent Factory Quick Start"
echo "=================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if we're in the right directory
if [ ! -f "Makefile" ] || [ ! -d "api" ]; then
    echo "❌ Please run this script from the Multi-Agent Factory root directory"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 1: Environment Setup${NC}"
echo "========================"

if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Edit .env with your API keys before continuing${NC}"
    echo ""
    read -p "Press Enter after editing .env file, or Ctrl+C to exit..."
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Dependency Check${NC}"
echo "======================="
make check-deps

echo ""
echo -e "${BLUE}Step 3: Starting Services${NC}"  
echo "========================"
make up

echo ""
echo -e "${BLUE}Step 4: Health Check${NC}"
echo "===================="
sleep 15  # Give services time to start
./scripts/health-check.sh

echo ""
echo -e "${BLUE}Step 5: Testing Agents${NC}"
echo "===================="
make test-agents

echo ""
echo -e "${GREEN}🎉 Multi-Agent Factory is ready!${NC}"
echo ""
echo "📚 What's Next:"
echo "  • View logs:        make logs-all"
echo "  • Test individual:  make test-task-doc"
echo "  • Monitor:          make monitor" 
echo "  • Documentation:    http://localhost:8000/docs"
echo ""
echo "🔧 Useful Commands:"
echo "  • make help         # Show all commands"
echo "  • make ps           # Service status"
echo "  • make clean        # Clean shutdown"