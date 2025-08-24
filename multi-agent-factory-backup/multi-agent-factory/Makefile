SHELL := /bin/bash
.DEFAULT_GOAL := help

# Load environment variables
ifneq (,$(wildcard .env))
    include .env
    export
endif

## Development Commands
.PHONY: up logs down ps curl setup test clean help

up: ## 🚀 Start all services
	@echo "🚀 Starting Multi-Agent Factory..."
	docker compose -f infra/docker/docker-compose.yml --env-file .env up --build -d
	@echo "✅ Services started. API available at http://localhost:8000"
	@echo "📊 Temporal UI at http://localhost:8080" 
	@echo "📝 To view logs: make logs"

logs: ## 📜 View API logs  
	docker compose -f infra/docker/docker-compose.yml logs -f api

logs-all: ## 📜 View all service logs
	docker compose -f infra/docker/docker-compose.yml logs -f

down: ## 🛑 Stop all services
	docker compose -f infra/docker/docker-compose.yml down

clean: ## 🧹 Stop and remove all containers, volumes
	docker compose -f infra/docker/docker-compose.yml down -v --remove-orphans
	docker system prune -f

ps: ## 📋 List running services
	docker compose -f infra/docker/docker-compose.yml ps

setup: ## ⚙️ Initial setup (copy env file)
	cp .env.example .env
	@echo "✅ Environment file created. Edit .env with your API keys."

## API Testing
curl: ## 🌐 Test API health endpoint
	@echo "Testing API health..."
	curl -s http://localhost:8000/ | jq . || echo "❌ API not responding"

test-task: ## 🧪 Submit a test task
	@echo "Submitting test documentation task..."
	curl -X POST http://localhost:8000/tasks \
		-H "Content-Type: application/json" \
		-d '{"task_id":"test-001","role":"doc_writer","payload":{"doc_type":"api","content":"Test API documentation"}}' \
		| jq .

list-agents: ## 👥 List available agents
	curl -s http://localhost:8000/agents | jq .

## Database Operations  
db-shell: ## 🗄️ Connect to database
	docker compose -f infra/docker/docker-compose.yml exec db psql -U user -d factory

redis-cli: ## 💾 Connect to Redis
	docker compose -f infra/docker/docker-compose.yml exec redis redis-cli

## Development 
install: ## 📦 Install Python dependencies locally
	pip install -r api/requirements.txt

format: ## 🎨 Format code with black
	black api/ orchestrator/ memory/ agents/

lint: ## 🔍 Lint code with flake8
	flake8 api/ orchestrator/ memory/ agents/

test: ## 🧪 Run tests
	python -m pytest tests/ -v

## Monitoring
stats: ## 📊 Show resource usage
	docker stats

help: ## 💡 Show this help message
	@echo "Multi-Agent Factory - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make setup  # Create .env file"  
	@echo "  make up     # Start all services"
	@echo "  make curl   # Test the API"
