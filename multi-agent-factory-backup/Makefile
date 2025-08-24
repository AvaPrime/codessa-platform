# File: Makefile
# Purpose: Unified developer/infra tooling + uv-based dependency management for Multi-Agent Factory

SHELL := /bin/bash
.DEFAULT_GOAL := help

# --------------------------------------------------------------------------------------
# Multi-Agent Factory — Unified Makefile
# Combines dev tooling (lint/format/typecheck/test) with infra controls (Docker Compose)
# --------------------------------------------------------------------------------------

# -------- Paths & Config --------
COMPOSE_FILE ?= infra/docker/docker-compose.yml
ENV_FILE     ?= .env
API_PORT     ?= 8000
API_HEALTH   ?= /
NATS_MONITOR ?= 8222

# Pretty colors
C := \033[36m
G := \033[32m
Y := \033[33m
R := \033[31m
E := \033[0m

# Docker Compose command (adds env-file automatically)
DC := docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE)

# Load environment variables from .env if present
ifneq (,$(wildcard $(ENV_FILE)))
	include $(ENV_FILE)
	export
endif

# -------- Phony targets --------
.PHONY: help verify setup env printenv \
        install install-dev install-test install-all lock venv \
        precommit lint lint-fix format format-check typecheck \
        test test-quick coverage \
        up up-dev down down-v reset restart ps logs tail stats top curl \
        compose-lint nats-health nats-pub scale \
        db-shell redis-cli \
        smoke e2e clean \
        backlog-validate backlog-report backlog-sprint backlog-owners backlog-metrics

# ======== Meta ========
help: ## Show this help
	@echo ""
	@echo "$(C)Multi-Agent Factory$(E) — commands"
	@echo ""
	@grep -E '^[a-zA-Z0-9_.-]+:.*?##' $(MAKEFILE_LIST) \
	 | sed -E 's/:.*?##/:##/' \
	 | awk 'BEGIN {FS=":##"} {printf "  $(C)%-24s$(E) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(Y)Quick start$(E): make setup && make up && make curl"

verify: ## Verify required tools and Compose syntax
	@echo "$(Y)Verifying local toolchain...$(E)"
	@command -v python >/dev/null 2>&1 || { echo "$(R)Missing: python$(E)"; exit 1; }
	@command -v uv >/dev/null 2>&1 || { echo "$(R)Missing: uv (pip install uv)$(E)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(R)Missing: docker$(E)"; exit 1; }
	@docker version >/dev/null 2>&1 || { echo "$(R)Docker daemon not responding$(E)"; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "$(R)Missing: docker compose$(E)"; exit 1; }
	@command -v curl >/dev/null 2>&1 || { echo "$(R)Missing: curl$(E)"; exit 1; }
	@command -v nats >/dev/null 2>&1 || { echo "$(Y)Note$(E): 'nats' CLI not found; messaging tests may be limited."; }
	@echo "$(Y)Linting compose file...$(E)"
	@$(DC) config -q || { echo "$(R)Compose config is invalid$(E)"; exit 1; }
	@echo "$(G)Verified: tools present and compose is valid$(E)"

setup: venv install-all ## Complete setup: create venv + install all deps
	@echo "Setup complete! Activate venv and you're ready to go."

env: printenv ## Print effective environment (from .env + shell)

printenv: ## Dump selected environment variables
	@echo "COMPOSE_FILE=$(COMPOSE_FILE)"
	@echo "ENV_FILE=$(ENV_FILE)"
	@echo "API_PORT=$(API_PORT)"
	@echo "API_HEALTH=$(API_HEALTH)"
	@echo "NATS_MONITOR=$(NATS_MONITOR)"
	@echo "POSTGRES_USER=$(POSTGRES_USER)"
	@echo "POSTGRES_DB=$(POSTGRES_DB)"

# ======== Dev Tooling ========
precommit: ## Install git hooks (pre-commit)
	pre-commit install

lint: ## Run static analysis (ruff + black check)
	ruff .
	black --check .

lint-fix: ## Auto-fix lint issues (ruff --fix + black)
	ruff --fix .
	black .

format: ## Format code (black)
	black .

format-check: ## Check formatting (black --check)
	black --check .

typecheck: ## Type checking (mypy)
	mypy .

test: ## Run test suite with coverage
	pytest -n auto --cov=. --cov-report=term-missing

test-quick: ## Fast local tests (no coverage, stop on first failure)
	pytest -q -x

test-matrix: ## Run streamlined test matrix (CI equivalent)
	@echo "$(Y)Running streamlined test matrix...$(E)"
	@echo "$(B)1. Sanity tests$(E)"
	pytest tests/test_sanity.py -v --tb=short
	@echo "$(B)2. Auth & Security$(E)"
	pytest tests/unit/test_api_auth.py tests/security/ -m "not slow" --cov=. --cov-report=term-missing:skip-covered --tb=short --maxfail=3 -q
	@echo "$(B)3. Core API$(E)"
	pytest tests/unit/ -k "not auth" -m "not slow and not integration" --cov=. --cov-report=term-missing:skip-covered --tb=short --maxfail=3 -q
	@echo "$(B)4. Agent Workflows$(E)"
	pytest tests/integration/test_task_workflow.py -m "integration" --tb=short --maxfail=3 -q || echo "$(Y)Integration tests require services$(E)"
	@echo "$(G)✅ Streamlined test matrix completed$(E)"

test-critical: ## Run only critical path tests
	@echo "$(Y)Running critical path tests...$(E)"
	pytest tests/test_sanity.py tests/unit/test_api_auth.py -m "not slow" --tb=short --maxfail=1 -q
	@echo "$(G)✅ Critical tests passed$(E)"

test-security: ## Run security-focused tests
	@echo "$(Y)Running security tests...$(E)"
	pytest tests/unit/test_api_auth.py tests/security/ -m "security or not slow" --cov=security --cov-report=term-missing --tb=short -v
	@echo "$(G)✅ Security tests completed$(E)"

test-integration: ## Run integration tests (requires services)
	@echo "$(Y)Running integration tests...$(E)"
	@echo "$(R)Note: Requires Redis and PostgreSQL services$(E)"
	pytest tests/integration/ -m "integration" --tb=short -v

test-validate: ## Validate test matrix configuration
	@echo "$(Y)Validating test matrix configuration...$(E)"
	python tests/test_matrix_config.py

validate: ## Validate changes before commit (full)
	@echo "$(Y)Running full change validation...$(E)"
	python scripts/validate_changes.py

validate-quick: ## Quick validation before commit
	@echo "$(Y)Running quick change validation...$(E)"
	python scripts/validate_changes.py --quick

validate-coverage: ## Validate with coverage reporting
	@echo "$(Y)Running validation with coverage...$(E)"
	python scripts/validate_changes.py --coverage

coverage: ## Generate HTML coverage report
	pytest --cov=. --cov-report=html
	@echo "$(G)Open htmlcov/index.html for details$(E)"

# === DEPENDENCY MANAGEMENT ===
install: ## Install production dependencies
	@echo "Installing production dependencies..."
	uv pip install -e .

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	uv pip install -e ".[dev]"

install-test: ## Install test dependencies
	@echo "Installing test dependencies..."
	uv pip install -e ".[test]"

install-all: ## Install all dependencies (dev + test)
	@echo "Installing all dependencies..."
	uv pip install -e ".[dev,test]"

lock: ## Generate lockfiles from pyproject.toml
	@echo "Generating lockfiles..."
	uv pip compile pyproject.toml -o requirements.txt
	uv pip compile --extra dev pyproject.toml -o requirements-dev.txt
	uv pip compile --extra test pyproject.toml -o requirements-test.txt

venv: ## Create virtual environment with uv
	@echo "Creating virtual environment..."
	uv venv
	@echo "Activate with: .venv\\Scripts\\activate (Windows) or source .venv/bin/activate (Unix)"

# ======== Infra Controls (Docker Compose) ========
up: ## Start full stack (production profile)
	@echo "$(Y)Starting services...$(E)"
	$(DC) up --build -d

up-dev: ## Start core stack with dev profile (api-dev, db, redis, nats)
	@echo "$(Y)Starting dev services...$(E)"
	$(DC) --profile dev up --build -d db redis nats api-dev

down: ## Stop stack (keep volumes)
	$(DC) down

down-v: ## Stop stack and remove volumes
	$(DC) down -v --remove-orphans

reset: ## Hard reset: stop, remove volumes, prune dangling resources
	$(MAKE) down-v
	docker volume prune -f || true

restart: ## Restart all services
	$(DC) restart

ps: ## List services & status
	$(DC) ps

logs: ## Show logs for a service: make logs S=api (use S=<service>)
	@[ -n "$(S)" ] || (echo "$(R)Usage: make logs S=<service>$(E)"; exit 1)
	$(DC) logs --since=10m $(S)

tail: ## Tail logs for a service: make tail S=api
	@[ -n "$(S)" ] || (echo "$(R)Usage: make tail S=<service>$(E)"; exit 1)
	$(DC) logs -f $(S)

stats: ## Live container resource usage
	docker stats

top: ## Show processes per service: make top S=api
	@[ -n "$(S)" ] || (echo "$(R)Usage: make top S=<service>$(E)"; exit 1)
	$(DC) top $(S)

curl: ## Probe API health
	@echo "GET http://127.0.0.1:$(API_PORT)$(API_HEALTH)"
	@curl -fsS --retry 20 --retry-connrefused --retry-delay 1 \
	  http://127.0.0.1:$(API_PORT)$(API_HEALTH) >/dev/null && \
	  echo "$(G)API is healthy$(E)" || \
	  (echo "$(R)API health check FAILED$(E)"; exit 1)

compose-lint: ## Validate docker-compose YAML (syntax/merge)
	$(DC) config -q && echo "$(G)Compose OK$(E)"

# ======== Messaging & Scaling ========
nats-health: ## Check NATS /healthz
	@curl -fsS http://127.0.0.1:$(NATS_MONITOR)/healthz | grep -q ok && \
	  echo "$(G)NATS is healthy$(E)" || \
	  (echo "$(R)NATS health check FAILED$(E)"; exit 1)

nats-pub: ## Publish a message via NATS CLI (SUBJECT=..., DATA='...')
	@[ -n "$(SUBJECT)" ] || (echo "$(R)Usage: make nats-pub SUBJECT=tasks.doc_writer DATA='{\"x\":1}'$(E)"; exit 1)
	@[ -n "$(DATA)" ] || (echo "$(R)Usage: make nats-pub SUBJECT=... DATA='...json...'$(E)"; exit 1)
	@nats pub "$(SUBJECT)" '$(DATA)'

scale: ## Scale a service: make scale S=doc-writer N=2
	@[ -n "$(S)" ] || (echo "$(R)Usage: make scale S=<service> N=<count>$(E)"; exit 1)
	@[ -n "$(N)" ] || (echo "$(R)Usage: make scale S=<service> N=<count>$(E)"; exit 1)
	$(DC) up -d --scale $(S)=$(N)

# ======== Shells ========
db-shell: ## Open psql in the db container
	$(DC) exec db psql -U "$${POSTGRES_USER:-user}" -d "$${POSTGRES_DB:-factory}"

redis-cli: ## Open redis-cli in the redis container
	$(DC) exec redis redis-cli

# ======== System-level checks ========
smoke: ## End-to-end smoke test (API + NATS)
	@echo "$(Y)Smoke: ensuring stack is up$(E)"
	$(MAKE) up
	@echo "$(Y)Smoke: waiting for API$(E)"
	@for i in $$(seq 1 60); do \
		if curl -fsS http://127.0.0.1:$(API_PORT)$(API_HEALTH) >/dev/null; then \
			echo "$(G)API ready$(E)"; break; \
		else \
			sleep 2; \
		fi; \
		if [ $$i -eq 60 ]; then echo "$(R)API not ready$(E)"; exit 1; fi; \
	done
	@echo "$(Y)Smoke: checking NATS$(E)"
	@curl -fsS http://127.0.0.1:$(NATS_MONITOR)/healthz | grep -q ok && echo "$(G)NATS ready$(E)" || (echo "$(R)NATS not ready$(E)"; exit 1)
	@echo "$(Y)Smoke: (optional) publish a test message with nats CLI$(E)"
	@echo "    nats pub tasks.doc_writer '{\"task_id\":\"smoke\",\"text\":\"hello\"}' || true"

e2e: ## Placeholder for a full end-to-end test suite
	@echo "Implement E2E tests here (e.g., pytest e2e/)."

clean: ## Clean up build artifacts and Docker resources
	@echo "$(Y)Cleaning up...$(E)"
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(G)Cleaned Python artifacts$(E)"
	@docker system prune -f || true
	@docker volume prune -f || true
	@docker network prune -f || true
	@docker image prune -f || true
	@docker container prune -f || true
	@docker builder prune -f || true
	@echo "$(G)Cleaned Docker resources$(E)"

# ======== Backlog Management ========
backlog-validate: ## Validate PROJECT_BACKLOG.md format and content
	@echo "$(Y)Validating project backlog...$(E)"
	@python scripts/backlog_manager.py validate
	@echo "$(G)Backlog validation complete$(E)"

backlog-report: ## Generate comprehensive backlog summary report
	@echo "$(Y)Generating backlog summary report...$(E)"
	@python scripts/backlog_manager.py report

backlog-report-json: ## Generate backlog summary report in JSON format
	@python scripts/backlog_manager.py report --format json

backlog-sprint: ## Generate current sprint report (usage: make backlog-sprint SPRINT=current)
	@echo "$(Y)Generating sprint report for: $(or $(SPRINT),current)$(E)"
	@python scripts/backlog_manager.py sprint-report $(or $(SPRINT),current)

backlog-sprint-json: ## Generate sprint report in JSON format
	@python scripts/backlog_manager.py sprint-report $(or $(SPRINT),current) --format json

backlog-owners: ## Generate workload report by team owners
	@echo "$(Y)Generating owner workload report...$(E)"
	@python scripts/backlog_manager.py owner-report

backlog-owners-json: ## Generate owner workload report in JSON format
	@python scripts/backlog_manager.py owner-report --format json

backlog-metrics: ## Show backlog metrics and statistics
	@echo "$(Y)Generating backlog metrics...$(E)"
	@python scripts/backlog_manager.py metrics

backlog-help: ## Show backlog management help and examples
	@echo "$(C)Backlog Management Commands:$(E)"
	@echo ""
	@echo "  $(G)make backlog-validate$(E)     - Validate backlog format"
	@echo "  $(G)make backlog-report$(E)       - Generate summary report"
	@echo "  $(G)make backlog-sprint$(E)       - Generate current sprint report"
	@echo "  $(G)make backlog-owners$(E)       - Generate owner workload report"
	@echo "  $(G)make backlog-metrics$(E)      - Show backlog statistics"
	@echo ""
	@echo "$(C)Examples:$(E)"
	@echo "  $(Y)make backlog-sprint SPRINT=next$(E)     - Next sprint report"
	@echo "  $(Y)make backlog-report-json$(E)            - JSON format report"
	@echo "  $(Y)make backlog-owners-json$(E)            - JSON owner report"
	@echo ""
