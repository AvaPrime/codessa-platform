#!/bin/bash
# Automated security updates script

set -euo pipefail

LOG_FILE="/var/log/maf/security_updates.log"
BACKUP_DIR="/backups/pre_update_$(date +%Y%m%d_%H%M%S)"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Notification function
notify() {
    local message="$1"
    local level="${2:-info}"
    
    log "$level: $message"
    
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"MAF Security Update [$level]: $message\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
}

# Backup function
backup_system() {
    log "Creating system backup..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    docker compose exec -T db pg_dump -U postgres multi_agent_factory > "$BACKUP_DIR/database.sql"
    
    # Backup configuration
    cp -r config/ "$BACKUP_DIR/config/"
    cp .env "$BACKUP_DIR/.env"
    
    # Backup Docker volumes
    docker run --rm -v maf_postgres_data:/data -v "$BACKUP_DIR:/backup" alpine \
        tar czf /backup/postgres_data.tar.gz -C /data .
    
    log "Backup completed: $BACKUP_DIR"
}

# Update Python dependencies
update_python_deps() {
    log "Updating Python dependencies..."
    
    # Check for vulnerabilities first
    if ! safety check; then
        notify "Vulnerabilities found in Python dependencies" "warning"
    fi
    
    # Update dependencies
    pip-compile --upgrade requirements.in
    pip-compile --upgrade requirements-dev.in
    pip-compile --upgrade requirements-test.in
    
    # Install updates
    pip-sync requirements.txt requirements-dev.txt requirements-test.txt
    
    log "Python dependencies updated"
}

# Update Docker images
update_docker_images() {
    log "Updating Docker images..."
    
    # Pull latest images
    docker compose pull
    
    # Scan for vulnerabilities
    for image in $(docker compose config --services); do
        log "Scanning $image for vulnerabilities..."
        if ! trivy image --exit-code 1 --severity HIGH,CRITICAL "$(docker compose images -q $image)"; then
            notify "High/Critical vulnerabilities found in $image" "error"
        fi
    done
    
    log "Docker images updated"
}

# Update system packages (if running on host)
update_system_packages() {
    if [[ "$EUID" -eq 0 ]] && command -v apt-get >/dev/null; then
        log "Updating system packages..."
        
        apt-get update
        apt-get upgrade -y
        apt-get autoremove -y
        
        # Check if reboot is required
        if [[ -f /var/run/reboot-required ]]; then
            notify "System reboot required after updates" "warning"
        fi
        
        log "System packages updated"
    fi
}

# Restart services
restart_services() {
    log "Restarting services..."
    
    # Graceful restart
    docker compose down
    docker compose up -d
    
    # Wait for services to be healthy
    sleep 30
    
    # Health check
    if curl -f http://localhost:8000/health; then
        log "Services restarted successfully"
        notify "Security updates completed successfully" "success"
    else
        log "Health check failed after restart"
        notify "Service restart failed - manual intervention required" "error"
        exit 1
    fi
}

# Main update process
main() {
    log "Starting security update process..."
    
    # Create backup
    backup_system
    
    # Update components
    update_python_deps
    update_docker_images
    update_system_packages
    
    # Restart services
    restart_services
    
    # Run security scan
    python scripts/security_scanner.py
    
    log "Security update process completed"
}

# Error handling
trap 'notify "Security update failed" "error"; exit 1' ERR

# Run main function
main "$@"