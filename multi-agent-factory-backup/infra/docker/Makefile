# Multi-Agent Factory Docker Makefile
# Simplifies Docker operations and agent management

.PHONY: help build up down logs clean test health scale backup restore

# Default target
help: ## Show this help message
	@echo "Multi-Agent Factory Docker Management"
	@echo "===================================="
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Environment setup
setup: ## Initial setup - copy env file and create secrets
	@echo "🔧 Setting up Multi-Agent Factory Docker environment..."
	@if [ ! -f ../../.env ]; then \
		cp ../../.env.example ../../.env; \
		echo "📝 Created .env file from template"; \
		echo "⚠️  Please edit .env with your configuration"; \
	else \
		echo "✅ .env file already exists"; \
	fi
	@mkdir -p secrets
	@echo "📁 Created secrets directory"
	@echo "🔐 Please add your secrets to the secrets/ directory"

# Build targets
build: ## Build all agent images
	@echo "🏗️  Building agent images..."
	docker compose build

build-no-cache: ## Build all images without cache
	@echo "🏗️  Building agent images (no cache)..."
	docker compose build --no-cache

build-agent: ## Build specific agent (usage: make build-agent AGENT=doc-writer)
	@if [ -z "$(AGENT)" ]; then \
		echo "❌ Please specify AGENT (e.g., make build-agent AGENT=doc-writer)"; \
		exit 1; \
	fi
	@echo "🏗️  Building $(AGENT) agent..."
	docker compose build $(AGENT)

# Deployment targets
up: ## Start all services
	@echo "🚀 Starting Multi-Agent Factory..."
	docker compose up -d
	@echo "✅ Services started"
	@make health

up-enhanced: ## Start with enhanced agent configuration
	@echo "🚀 Starting Multi-Agent Factory with enhanced agents..."
	docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d
	@echo "✅ Enhanced services started"

up-obs: ## Start with observability stack
	@echo "🚀 Starting Multi-Agent Factory with observability..."
	docker compose --profile obs up -d
	@echo "✅ Services with observability started"
	@echo "📊 Prometheus: http://localhost:9090"
	@echo "📈 Grafana: http://localhost:3000"
	@echo "🔍 Jaeger: http://localhost:16686"

up-secure: ## Start with security hardening
	@echo "🚀 Starting Multi-Agent Factory with security hardening..."
	docker compose -f docker-compose.yml -f docker-compose.security.yml up -d
	@echo "✅ Secure services started"

up-dev: ## Start in development mode
	@echo "🚀 Starting Multi-Agent Factory in development mode..."
	docker compose --profile dev up -d
	@echo "✅ Development services started"

down: ## Stop all services
	@echo "🛑 Stopping Multi-Agent Factory..."
	docker compose down
	@echo "✅ Services stopped"

down-volumes: ## Stop all services and remove volumes (⚠️ DATA LOSS)
	@echo "⚠️  This will remove all data volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "🛑 Stopping services and removing volumes..."; \
		docker compose down -v; \
		echo "✅ Services stopped and volumes removed"; \
	else \
		echo ""; \
		echo "❌ Operation cancelled"; \
	fi

restart: ## Restart all services
	@echo "🔄 Restarting Multi-Agent Factory..."
	docker compose restart
	@echo "✅ Services restarted"

restart-agent: ## Restart specific agent (usage: make restart-agent AGENT=doc-writer)
	@if [ -z "$(AGENT)" ]; then \
		echo "❌ Please specify AGENT (e.g., make restart-agent AGENT=doc-writer)"; \
		exit 1; \
	fi
	@echo "🔄 Restarting $(AGENT) agent..."
	docker compose restart $(AGENT)
	@echo "✅ $(AGENT) restarted"

# Monitoring and logs
logs: ## Show logs for all services
	docker compose logs -f

logs-agent: ## Show logs for specific agent (usage: make logs-agent AGENT=doc-writer)
	@if [ -z "$(AGENT)" ]; then \
		echo "❌ Please specify AGENT (e.g., make logs-agent AGENT=doc-writer)"; \
		exit 1; \
	fi
	docker compose logs -f $(AGENT)

status: ## Show service status
	@echo "📊 Multi-Agent Factory Status"
	@echo "============================="
	docker compose ps

health: ## Check health of all services
	@echo "🏥 Health Check Results"
	@echo "======================"
	@for service in $$(docker compose ps --services); do \
		echo -n "$$service: "; \
		if docker compose exec -T $$service curl -sf http://localhost:8080/health >/dev/null 2>&1; then \
			echo "✅ Healthy"; \
		else \
			echo "❌ Unhealthy"; \
		fi; \
	done 2>/dev/null || echo "⚠️  Some services may not have health endpoints"

stats: ## Show resource usage statistics
	@echo "📈 Resource Usage Statistics"
	@echo "============================"
	docker stats --no-stream

# Scaling
scale: ## Scale services (usage: make scale SERVICE=doc-writer REPLICAS=3)
	@if [ -z "$(SERVICE)" ] || [ -z "$(REPLICAS)" ]; then \
		echo "❌ Please specify SERVICE and REPLICAS (e.g., make scale SERVICE=doc-writer REPLICAS=3)"; \
		exit 1; \
	fi
	@echo "📈 Scaling $(SERVICE) to $(REPLICAS) replicas..."
	docker compose up --scale $(SERVICE)=$(REPLICAS) -d
	@echo "✅ $(SERVICE) scaled to $(REPLICAS) replicas"

scale-down: ## Scale down all services to 1 replica
	@echo "📉 Scaling down all services..."
	docker compose up --scale doc-writer=1 --scale frontend-dev=1 --scale backend-dev=1 --scale compliance-checker=1 --scale qa-tester=1 -d
	@echo "✅ All services scaled down"

# Development and testing
shell: ## Open shell in specific agent (usage: make shell AGENT=doc-writer)
	@if [ -z "$(AGENT)" ]; then \
		echo "❌ Please specify AGENT (e.g., make shell AGENT=doc-writer)"; \
		exit 1; \
	fi
	@echo "🐚 Opening shell in $(AGENT)..."
	docker compose exec $(AGENT) bash

test: ## Run tests in test environment
	@echo "🧪 Running tests..."
	docker compose -f ../tests/docker-compose.test.yml up --build --abort-on-container-exit
	docker compose -f ../tests/docker-compose.test.yml down

validate: ## Validate Docker Compose configuration
	@echo "✅ Validating Docker Compose configuration..."
	docker compose config > /dev/null
	@echo "✅ Configuration is valid"

validate-enhanced: ## Validate enhanced configuration
	@echo "✅ Validating enhanced Docker Compose configuration..."
	docker compose -f docker-compose.yml -f docker-compose.agents.yml config > /dev/null
	@echo "✅ Enhanced configuration is valid"

# Maintenance
clean: ## Clean up unused Docker resources
	@echo "🧹 Cleaning up Docker resources..."
	docker system prune -f
	docker volume prune -f
	docker network prune -f
	@echo "✅ Cleanup completed"

clean-all: ## Clean up all Docker resources (⚠️ DESTRUCTIVE)
	@echo "⚠️  This will remove ALL Docker resources!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "🧹 Cleaning up all Docker resources..."; \
		docker system prune -a -f --volumes; \
		echo "✅ All Docker resources cleaned"; \
	else \
		echo ""; \
		echo "❌ Operation cancelled"; \
	fi

update: ## Update base images and rebuild
	@echo "🔄 Updating base images..."
	docker compose pull
	@echo "🏗️  Rebuilding images..."
	docker compose build --pull
	@echo "🚀 Restarting services..."
	docker compose up -d --force-recreate
	@echo "✅ Update completed"

# Backup and restore
backup: ## Create backup of volumes and configuration
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	echo "📦 Backing up database..."; \
	docker run --rm -v maf_dbdata:/data -v $$(pwd)/backups:/backup alpine tar czf /backup/db-$$timestamp.tar.gz -C /data .; \
	echo "📦 Backing up Redis..."; \
	docker run --rm -v maf_redisdata:/data -v $$(pwd)/backups:/backup alpine tar czf /backup/redis-$$timestamp.tar.gz -C /data .; \
	echo "📦 Backing up configuration..."; \
	tar czf backups/config-$$timestamp.tar.gz .env secrets/ docker-compose*.yml; \
	echo "✅ Backup completed: backups/*-$$timestamp.tar.gz"

restore: ## Restore from backup (usage: make restore BACKUP=20240115_143000)
	@if [ -z "$(BACKUP)" ]; then \
		echo "❌ Please specify BACKUP timestamp (e.g., make restore BACKUP=20240115_143000)"; \
		echo "Available backups:"; \
		ls -1 backups/ | grep -E '\.(tar\.gz)$$' | sed 's/.*-\([0-9_]*\)\.tar\.gz/\1/' | sort -u; \
		exit 1; \
	fi
	@echo "⚠️  This will restore data from backup $(BACKUP)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "🛑 Stopping services..."; \
		docker compose down; \
		echo "📦 Restoring database..."; \
		docker run --rm -v maf_dbdata:/data -v $$(pwd)/backups:/backup alpine tar xzf /backup/db-$(BACKUP).tar.gz -C /data; \
		echo "📦 Restoring Redis..."; \
		docker run --rm -v maf_redisdata:/data -v $$(pwd)/backups:/backup alpine tar xzf /backup/redis-$(BACKUP).tar.gz -C /data; \
		echo "📦 Restoring configuration..."; \
		tar xzf backups/config-$(BACKUP).tar.gz; \
		echo "🚀 Starting services..."; \
		docker compose up -d; \
		echo "✅ Restore completed"; \
	else \
		echo ""; \
		echo "❌ Operation cancelled"; \
	fi

# Security
security-scan: ## Run security scan on images
	@echo "🔒 Running security scan..."
	@for image in $$(docker compose config | grep 'image:' | awk '{print $$2}' | sort -u); do \
		echo "Scanning $$image..."; \
		docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image $$image; \
	done

security-audit: ## Run comprehensive security audit
	@echo "🔒 Running security audit..."
	@python ../../scripts/security_audit.py --docker

# Documentation
docs: ## Generate documentation
	@echo "📚 Generating documentation..."
	@echo "Docker configuration documented in README.md"
	@echo "Agent services: $$(docker compose config --services | wc -l) services configured"
	@echo "Networks: $$(docker compose config --volumes | wc -l) networks configured"
	@echo "Volumes: $$(docker compose config --volumes | wc -l) volumes configured"

# Quick commands
quick-start: setup build up ## Quick start - setup, build, and run
	@echo "🎉 Multi-Agent Factory is ready!"
	@echo "📊 API: http://localhost:8000"
	@echo "🔍 Health checks: make health"
	@echo "📝 Logs: make logs"

quick-dev: setup build up-dev up-obs ## Quick development setup with observability
	@echo "🎉 Development environment ready!"
	@echo "📊 API: http://localhost:8000"
	@echo "📈 Grafana: http://localhost:3000"
	@echo "🔍 Jaeger: http://localhost:16686"

# Environment info
info: ## Show environment information
	@echo "ℹ️  Multi-Agent Factory Docker Environment"
	@echo "========================================="
	@echo "Docker version: $$(docker --version)"
	@echo "Docker Compose version: $$(docker compose version)"
	@echo "Current directory: $$(pwd)"
	@echo "Environment file: $$([ -f ../../.env ] && echo '✅ Found' || echo '❌ Missing')"
	@echo "Secrets directory: $$([ -d secrets ] && echo '✅ Found' || echo '❌ Missing')"
	@echo "Available services: $$(docker compose config --services | tr '\n' ' ')"
	@echo "Running services: $$(docker compose ps --services --filter status=running | tr '\n' ' ')"