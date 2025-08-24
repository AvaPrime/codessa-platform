#!/bin/bash
# Multi-Agent Factory - Agent Entrypoint Script
# Handles agent initialization, health checks, and graceful shutdown

set -euo pipefail

# Configuration
AGENT_ROLE="${AGENT_ROLE:-}"
ENV="${ENV:-prod}"
DEBUG="${DEBUG:-false}"
HEALTH_CHECK_PORT="${HEALTH_CHECK_PORT:-8080}"
GRACEFUL_SHUTDOWN_TIMEOUT="${GRACEFUL_SHUTDOWN_TIMEOUT:-30}"

# Logging configuration
LOG_LEVEL="${LOG_LEVEL:-INFO}"
LOG_FORMAT="${LOG_FORMAT:-json}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
    fi
}

# Cleanup function for graceful shutdown
cleanup() {
    log_info "Received shutdown signal, initiating graceful shutdown..."
    
    if [[ -n "${AGENT_PID:-}" ]]; then
        log_info "Stopping agent process (PID: $AGENT_PID)..."
        kill -TERM "$AGENT_PID" 2>/dev/null || true
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 "$AGENT_PID" 2>/dev/null && [[ $count -lt $GRACEFUL_SHUTDOWN_TIMEOUT ]]; do
            sleep 1
            ((count++))
        done
        
        # Force kill if still running
        if kill -0 "$AGENT_PID" 2>/dev/null; then
            log_warn "Agent did not shutdown gracefully, forcing termination..."
            kill -KILL "$AGENT_PID" 2>/dev/null || true
        fi
    fi
    
    log_info "Agent shutdown complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

# Validation functions
validate_environment() {
    log_info "Validating environment configuration..."
    
    if [[ -z "$AGENT_ROLE" ]]; then
        log_error "AGENT_ROLE environment variable is required"
        exit 1
    fi
    
    if [[ ! -f "agents/${AGENT_ROLE}/agent.py" ]]; then
        log_error "Agent script not found: agents/${AGENT_ROLE}/agent.py"
        log_error "Available agents:"
        find agents -name "agent.py" -type f | sed 's|agents/||g' | sed 's|/agent.py||g' | sort
        exit 1
    fi
    
    # Check required environment variables
    local required_vars=("POSTGRES_URI" "REDIS_HOST" "NATS_URL")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_info "Environment validation passed"
}

# Health check function
start_health_server() {
    log_info "Starting health check server on port $HEALTH_CHECK_PORT..."
    
    python3 -c "
import http.server
import socketserver
import json
import os
import threading
import time
from datetime import datetime

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            try:
                # Basic health check
                health_data = {
                    'status': 'healthy',
                    'agent_role': os.environ.get('AGENT_ROLE', 'unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'uptime': time.time() - start_time,
                    'environment': os.environ.get('ENV', 'unknown')
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(health_data).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_data = {'status': 'unhealthy', 'error': str(e)}
                self.wfile.write(json.dumps(error_data).encode())
        elif self.path == '/ready':
            # Readiness check - can be enhanced with specific agent checks
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'ready')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress default logging

start_time = time.time()
with socketserver.TCPServer(('', $HEALTH_CHECK_PORT), HealthHandler) as httpd:
    httpd.serve_forever()
" &
    
    HEALTH_SERVER_PID=$!
    log_debug "Health server started with PID: $HEALTH_SERVER_PID"
}

# Wait for dependencies
wait_for_dependencies() {
    log_info "Waiting for dependencies to be ready..."
    
    # Wait for database
    log_info "Checking database connectivity..."
    python3 -c "
import psycopg
import os
import time
import sys

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        conn = psycopg.connect(os.environ['POSTGRES_URI'])
        conn.close()
        print('Database connection successful')
        sys.exit(0)
    except Exception as e:
        attempt += 1
        print(f'Database connection attempt {attempt}/{max_attempts} failed: {e}')
        if attempt < max_attempts:
            time.sleep(2)
        else:
            sys.exit(1)
"
    
    # Wait for Redis
    log_info "Checking Redis connectivity..."
    python3 -c "
import redis
import os
import time
import sys

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        r = redis.Redis(host=os.environ['REDIS_HOST'], port=int(os.environ.get('REDIS_PORT', 6379)))
        r.ping()
        print('Redis connection successful')
        sys.exit(0)
    except Exception as e:
        attempt += 1
        print(f'Redis connection attempt {attempt}/{max_attempts} failed: {e}')
        if attempt < max_attempts:
            time.sleep(2)
        else:
            sys.exit(1)
"
    
    # Wait for NATS
    log_info "Checking NATS connectivity..."
    python3 -c "
import asyncio
import nats
import os
import sys

async def check_nats():
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            nc = await nats.connect(os.environ['NATS_URL'])
            await nc.close()
            print('NATS connection successful')
            return True
        except Exception as e:
            attempt += 1
            print(f'NATS connection attempt {attempt}/{max_attempts} failed: {e}')
            if attempt < max_attempts:
                await asyncio.sleep(2)
            else:
                return False
    return False

if not asyncio.run(check_nats()):
    sys.exit(1)
"
    
    log_info "All dependencies are ready"
}

# Pre-flight checks
pre_flight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check Python modules
    python3 -c "
import importlib.util
import os
import sys

role = os.environ.get('AGENT_ROLE', '')
if not role:
    print('AGENT_ROLE not set')
    sys.exit(1)

spec = importlib.util.find_spec(f'agents.{role}.agent')
if not spec:
    print(f'Agent module agents.{role}.agent not found')
    sys.exit(1)

print(f'Agent module agents.{role}.agent found and importable')
"
    
    # Check permissions
    if [[ ! -w "/app/logs" ]]; then
        log_error "Cannot write to logs directory"
        exit 1
    fi
    
    if [[ ! -w "/app/tmp" ]]; then
        log_error "Cannot write to temp directory"
        exit 1
    fi
    
    log_info "Pre-flight checks passed"
}

# Main execution
main() {
    log_info "Starting Multi-Agent Factory Agent: $AGENT_ROLE"
    log_info "Environment: $ENV"
    log_info "Debug mode: $DEBUG"
    
    # Run validation and checks
    validate_environment
    wait_for_dependencies
    pre_flight_checks
    
    # Start health check server
    start_health_server
    
    # Start the agent
    log_info "Starting agent: $AGENT_ROLE"
    
    # Set up logging for the agent
    export PYTHONUNBUFFERED=1
    export PYTHONFAULTHANDLER=1
    
    # Start agent with proper signal handling
    python3 -u "agents/${AGENT_ROLE}/agent.py" &
    AGENT_PID=$!
    
    log_info "Agent started with PID: $AGENT_PID"
    
    # Wait for agent to finish or receive signal
    wait $AGENT_PID
    AGENT_EXIT_CODE=$?
    
    if [[ $AGENT_EXIT_CODE -eq 0 ]]; then
        log_info "Agent exited normally"
    else
        log_error "Agent exited with code: $AGENT_EXIT_CODE"
    fi
    
    # Cleanup
    if [[ -n "${HEALTH_SERVER_PID:-}" ]]; then
        kill $HEALTH_SERVER_PID 2>/dev/null || true
    fi
    
    exit $AGENT_EXIT_CODE
}

# Execute main function
main "$@"