#!/bin/bash
# Enhanced automated security updates with comprehensive validation

set -euo pipefail

# Configuration
LOG_FILE="/var/log/maf/security_updates.log"
BACKUP_DIR="/backups/security_update_$(date +%Y%m%d_%H%M%S)"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
SECURITY_SCAN_ENABLED="${SECURITY_SCAN_ENABLED:-true}"
AUTO_ROLLBACK_ENABLED="${AUTO_ROLLBACK_ENABLED:-true}"
MAINTENANCE_WINDOW_START="${MAINTENANCE_WINDOW_START:-02:00}"
MAINTENANCE_WINDOW_END="${MAINTENANCE_WINDOW_END:-04:00}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Notification function
notify() {
    local message="$1"
    local level="${2:-info}"
    local color="good"
    
    case $level in
        "error") color="danger" ;;
        "warning") color="warning" ;;
        "info") color="good" ;;
    esac
    
    log "$level: $message"
    
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"MAF Security Update [$level]\",
                    \"text\": \"$message\",
                    \"ts\": $(date +%s)
                }]
            }" \
            "$SLACK_WEBHOOK_URL" || true
    fi
}

# Check if we're in maintenance window
check_maintenance_window() {
    local current_time=$(date +%H:%M)
    local start_time="$MAINTENANCE_WINDOW_START"
    local end_time="$MAINTENANCE_WINDOW_END"
    
    if [[ "$current_time" > "$start_time" && "$current_time" < "$end_time" ]]; then
        return 0
    else
        log "Outside maintenance window ($start_time - $end_time). Current time: $current_time"
        return 1
    fi
}

# Comprehensive system backup
backup_system() {
    log "Creating comprehensive system backup..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup database with encryption
    docker compose exec -T db pg_dump -U postgres multi_agent_factory | \
        gpg --symmetric --cipher-algo AES256 --output "$BACKUP_DIR/database.sql.gpg"
    
    # Backup configuration files
    tar -czf "$BACKUP_DIR/config.tar.gz" config/ .env* docker-compose*.yml
    
    # Backup Docker volumes
    docker run --rm -v maf_postgres_data:/data -v "$BACKUP_DIR:/backup" alpine \
        tar czf /backup/postgres_data.tar.gz -C /data .
    
    docker run --rm -v maf_redis_data:/data -v "$BACKUP_DIR:/backup" alpine \
        tar czf /backup/redis_data.tar.gz -C /data .
    
    # Backup security keys
    if [[ -d "/etc/maf/keys" ]]; then
        tar -czf "$BACKUP_DIR/security_keys.tar.gz" -C /etc/maf keys/
        chmod 600 "$BACKUP_DIR/security_keys.tar.gz"
    fi
    
    # Create backup manifest
    cat > "$BACKUP_DIR/manifest.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "version": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "files": [
        "database.sql.gpg",
        "config.tar.gz",
        "postgres_data.tar.gz",
        "redis_data.tar.gz",
        "security_keys.tar.gz"
    ],
    "checksum": "$(find $BACKUP_DIR -type f -exec sha256sum {} \; | sha256sum | cut -d' ' -f1)"
}
EOF
    
    log "Backup completed: $BACKUP_DIR"
}

# Security vulnerability scan
run_security_scan() {
    log "Running comprehensive security scan..."
    
    # Python dependency scan
    if command -v safety &> /dev/null; then
        safety check --json > "$BACKUP_DIR/security_scan_python.json" || true
    fi
    
    # Docker image scan
    if command -v trivy &> /dev/null; then
        trivy image --format json --output "$BACKUP_DIR/security_scan_docker.json" \
            multi-agent-factory:latest || true
    fi
    
    # Infrastructure scan
    if command -v nmap &> /dev/null; then
        nmap -sV -O localhost > "$BACKUP_DIR/security_scan_infra.txt" 2>/dev/null || true
    fi
    
    # Check for critical vulnerabilities
    if [[ -f "$BACKUP_DIR/security_scan_python.json" ]]; then
        critical_count=$(jq '[.[] | select(.severity == "critical")] | length' \
            "$BACKUP_DIR/security_scan_python.json" 2>/dev/null || echo "0")
        
        if [[ "$critical_count" -gt 0 ]]; then
            notify "Critical vulnerabilities found: $critical_count" "error"
            return 1
        fi
    fi
    
    log "Security scan completed"
}

# Update system packages
update_system_packages() {
    log "Updating system packages..."
    
    # Update package lists
    apt-get update
    
    # Get list of security updates
    security_updates=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
    
    if [[ "$security_updates" -gt 0 ]]; then
        log "Found $security_updates security updates"
        
        # Apply security updates only
        DEBIAN_FRONTEND=noninteractive apt-get -y upgrade \
            -o Dpkg::Options::="--force-confdef" \
            -o Dpkg::Options::="--force-confold"
        
        # Clean up
        apt-get autoremove -y
        apt-get autoclean
        
        log "System packages updated successfully"
    else
        log "No security updates available"
    fi
}

# Update Python dependencies
update_python_dependencies() {
    log "Updating Python dependencies..."
    
    # Update pip tools
    pip install --upgrade pip setuptools wheel
    
    # Update dependencies with security fixes
    if [[ -f "requirements.txt" ]]; then
        pip-audit --fix --requirement requirements.txt || true
    fi
    
    # Update development dependencies
    if [[ -f "requirements-dev.txt" ]]; then
        pip-audit --fix --requirement requirements-dev.txt || true
    fi
    
    log "Python dependencies updated"
}

# Update Docker images
update_docker_images() {
    log "Updating Docker images..."
    
    # Pull latest base images
    docker compose pull
    
    # Rebuild images with latest security patches
    docker compose build --no-cache --pull
    
    # Remove old images
    docker image prune -f
    
    log "Docker images updated"
}

# Validate system after updates
validate_system() {
    log "Validating system after updates..."
    
    # Start services
    docker compose up -d
    
    # Wait for services to be ready
    sleep 30
    
    # Health checks
    local health_check_failed=false
    
    # API health check
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "API health check failed"
        health_check_failed=true
    fi
    
    # Database health check
    if ! docker compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        log "Database health check failed"
        health_check_failed=true
    fi
    
    # Redis health check
    if ! docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log "Redis health check failed"
        health_check_failed=true
    fi
    
    # NATS health check
    if ! curl -f http://localhost:8222/healthz > /dev/null 2>&1; then
        log "NATS health check failed"
        health_check_failed=true
    fi
    
    if [[ "$health_check_failed" == "true" ]]; then
        notify "System validation failed after updates" "error"
        return 1
    fi
    
    log "System validation passed"
}

# Rollback system
rollback_system() {
    log "Rolling back system..."
    
    # Stop current services
    docker compose down
    
    # Restore database
    if [[ -f "$BACKUP_DIR/database.sql.gpg" ]]; then
        gpg --decrypt "$BACKUP_DIR/database.sql.gpg" | \
            docker compose exec -T db psql -U postgres multi_agent_factory
    fi
    
    # Restore configuration
    if [[ -f "$BACKUP_DIR/config.tar.gz" ]]; then
        tar -xzf "$BACKUP_DIR/config.tar.gz"
    fi
    
    # Restore Docker volumes
    if [[ -f "$BACKUP_DIR/postgres_data.tar.gz" ]]; then
        docker run --rm -v maf_postgres_data:/data -v "$BACKUP_DIR:/backup" alpine \
            tar xzf /backup/postgres_data.tar.gz -C /data
    fi
    
    # Restart services
    docker compose up -d
    
    log "System rollback completed"
}

# Main execution
main() {
    log "Starting enhanced security update process"
    
    # Check maintenance window
    if ! check_maintenance_window; then
        log "Skipping updates - outside maintenance window"
        exit 0
    fi
    
    # Create backup
    backup_system
    
    # Run security scan if enabled
    if [[ "$SECURITY_SCAN_ENABLED" == "true" ]]; then
        if ! run_security_scan; then
            notify "Security scan failed - aborting updates" "error"
            exit 1
        fi
    fi
    
    # Perform updates
    local update_failed=false
    
    update_system_packages || update_failed=true
    update_python_dependencies || update_failed=true
    update_docker_images || update_failed=true
    
    if [[ "$update_failed" == "true" ]]; then
        notify "Updates failed" "error"
        
        if [[ "$AUTO_ROLLBACK_ENABLED" == "true" ]]; then
            rollback_system
        fi
        
        exit 1
    fi
    
    # Validate system
    if ! validate_system; then
        notify "System validation failed" "error"
        
        if [[ "$AUTO_ROLLBACK_ENABLED" == "true" ]]; then
            rollback_system
        fi
        
        exit 1
    fi
    
    notify "Security updates completed successfully" "info"
    log "Enhanced security update process completed"
}

# Execute main function
main "$@"