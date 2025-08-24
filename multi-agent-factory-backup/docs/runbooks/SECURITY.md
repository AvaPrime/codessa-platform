# 🔒 Multi-Agent Factory Security and Compliance Guide

---
title: Security and Compliance Runbook
owner: Security Team
version: 1.0
last_reviewed: 2025-01-20
next_review: 2025-04-20
status: operational
classification: internal
---

## 🛡️ Security Overview

This runbook covers security procedures, compliance requirements, and incident response for the Multi-Agent Factory system.

## 🔐 Authentication & Authorization

### JWT Token Management

#### Token Generation
```bash
# Generate new JWT token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'
```

#### Token Validation
```python
# Validate token programmatically
import jwt
from api.auth import JWT_SECRET_KEY

def validate_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
```

#### Token Revocation
```bash
# Revoke compromised token
curl -X POST http://localhost:8000/auth/revoke \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"token": "<token_to_revoke>"}'
```

### API Key Security

#### Rotation Procedure
1. Generate new API key from provider
2. Update `.env` file with new key
3. Restart services: `make restart`
4. Verify functionality: `make test-agents`
5. Revoke old API key from provider

#### Key Storage
- **Development**: Use `.env` file (never commit)
- **Production**: Use external secret manager (AWS Secrets Manager, HashiCorp Vault)
- **Kubernetes**: Use sealed secrets or external secrets operator

### Access Control

#### Role-Based Access Control (RBAC)
```yaml
# config/rbac.yaml
roles:
  admin:
    permissions:
      - "tasks:create"
      - "tasks:read"
      - "tasks:delete"
      - "agents:manage"
      - "system:admin"
  
  user:
    permissions:
      - "tasks:create"
      - "tasks:read"
  
  readonly:
    permissions:
      - "tasks:read"
```

#### Scope Validation
```python
# Example scope check
from api.auth import require_scope

@app.post("/admin/agents")
@require_scope("agents:manage")
async def manage_agents(user: User = Depends(get_current_user)):
    # Admin-only functionality
    pass
```

## 🔍 Security Monitoring

### Failed Authentication Attempts
```bash
# Monitor failed login attempts
grep "authentication failed" /var/log/maf/api.log | tail -20

# Check for brute force patterns
awk '/authentication failed/ {print $1, $2, $7}' /var/log/maf/api.log | sort | uniq -c | sort -nr
```

### Suspicious Activity Detection
```bash
# Monitor unusual API usage patterns
grep "rate_limit_exceeded" /var/log/maf/api.log

# Check for unusual task submissions
grep "task_created" /var/log/maf/api.log | awk '{print $7}' | sort | uniq -c | sort -nr
```

### Security Alerts
```yaml
# prometheus/alerts.yml
groups:
  - name: security
    rules:
      - alert: HighFailedAuthRate
        expr: rate(auth_failures_total[5m]) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High authentication failure rate detected"
      
      - alert: UnauthorizedAccess
        expr: rate(http_requests_total{status="401"}[5m]) > 5
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Multiple unauthorized access attempts"
```

## 🛡️ Data Protection

### Encryption at Rest
```bash
# PostgreSQL encryption
# Enable in postgresql.conf
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
```

### Encryption in Transit
```yaml
# docker-compose.yml - Enable TLS
services:
  nats:
    command: [
      "--tls",
      "--tlscert=/certs/server.crt",
      "--tlskey=/certs/server.key"
    ]
```

### Data Sanitization
```python
# Input sanitization example
from bleach import clean
from html import escape

def sanitize_input(user_input: str) -> str:
    # Remove HTML tags and escape special characters
    cleaned = clean(user_input, tags=[], strip=True)
    return escape(cleaned)
```

## 🚨 Incident Response

### Security Incident Classification

#### P0 - Critical Security Incident
- Data breach or unauthorized access to sensitive data
- System compromise or malware detection
- Active attack in progress

**Response Time**: Immediate (< 5 minutes)

#### P1 - High Security Incident
- Suspicious activity patterns
- Failed security controls
- Potential vulnerability exploitation

**Response Time**: 15 minutes

### Incident Response Procedures

#### Immediate Response (0-15 minutes)
1. **Assess and Contain**
   ```bash
   # Isolate affected systems
   docker compose stop <affected_service>
   
   # Block suspicious IPs
   iptables -A INPUT -s <suspicious_ip> -j DROP
   
   # Revoke compromised tokens
   curl -X POST http://localhost:8000/auth/revoke-all
   ```

2. **Preserve Evidence**
   ```bash
   # Capture logs
   docker compose logs > incident_logs_$(date +%Y%m%d_%H%M%S).log
   
   # Database snapshot
   pg_dump -h localhost -U postgres multi_agent_factory > db_snapshot_$(date +%Y%m%d_%H%M%S).sql
   ```

3. **Notify Stakeholders**
   - Security team: security@company.com
   - On-call engineer: +1-555-ON-CALL
   - Management (for P0 incidents)

#### Investigation Phase (15 minutes - 4 hours)

1. **Log Analysis**
   ```bash
   # Analyze access patterns
   grep -E "(POST|PUT|DELETE)" /var/log/maf/api.log | grep -v "200\|201"
   
   # Check for data exfiltration
   grep "large_response" /var/log/maf/api.log
   
   # Review authentication logs
   grep "auth" /var/log/maf/api.log | tail -100
   ```

2. **System Integrity Check**
   ```bash
   # Check file integrity
   find /app -type f -name "*.py" -exec sha256sum {} \; > current_checksums.txt
   diff baseline_checksums.txt current_checksums.txt
   
   # Verify container images
   docker images --digests
   ```

3. **Network Analysis**
   ```bash
   # Check network connections
   netstat -tulpn | grep -E "(8000|5432|6379|4222)"
   
   # Review firewall logs
   tail -100 /var/log/ufw.log
   ```

### Recovery Procedures

#### Clean Recovery
```bash
# 1. Stop all services
make down

# 2. Update to latest secure version
git pull origin main

# 3. Rotate all secrets
./scripts/rotate_secrets.sh

# 4. Rebuild containers
docker compose build --no-cache

# 5. Start with clean state
make up

# 6. Verify security
./scripts/security_check.sh
```

#### Data Recovery
```bash
# Restore from backup if data integrity is compromised
psql -h localhost -U postgres -d multi_agent_factory < backup_$(date -d "yesterday" +%Y%m%d).sql
```

## 📋 Compliance Requirements

### GDPR Compliance

#### Data Subject Rights
```python
# Data export endpoint
@app.get("/user/{user_id}/data")
@require_scope("data:export")
async def export_user_data(user_id: str):
    # Export all user data in machine-readable format
    pass

# Data deletion endpoint
@app.delete("/user/{user_id}/data")
@require_scope("data:delete")
async def delete_user_data(user_id: str):
    # Permanently delete all user data
    pass
```

#### Data Retention
```sql
-- Automated data cleanup
DELETE FROM tasks WHERE created_at < NOW() - INTERVAL '7 days' AND status = 'completed';
DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '30 days';
```

### SOC 2 Compliance

#### Access Logging
```python
# Audit log example
import logging

audit_logger = logging.getLogger('audit')

def log_access(user_id: str, resource: str, action: str):
    audit_logger.info(f"User {user_id} performed {action} on {resource}")
```

#### Change Management
```bash
# All changes must be tracked
git log --oneline --since="1 week ago" > weekly_changes.log
```

## 🔧 Security Tools

### Vulnerability Scanning
```bash
# Container scanning
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image multi-agent-factory:latest

# Dependency scanning
safety check

# Code scanning
bandit -r . -f json -o security_report.json
```

### Penetration Testing
```bash
# API security testing
nmap -sV -sC localhost -p 8000

# SQL injection testing
sqlmap -u "http://localhost:8000/api/tasks" --data="{\"role\":\"test\"}" --headers="Content-Type: application/json"
```

## 📊 Security Metrics

### Key Performance Indicators
- Authentication failure rate: < 1%
- Mean time to detect (MTTD): < 5 minutes
- Mean time to respond (MTTR): < 15 minutes
- Vulnerability remediation time: < 24 hours (critical), < 7 days (high)

### Monitoring Dashboard
```yaml
# Grafana dashboard config
dashboard:
  title: "Security Metrics"
  panels:
    - title: "Authentication Failures"
      type: "stat"
      targets:
        - expr: "rate(auth_failures_total[5m])"
    
    - title: "Active Sessions"
      type: "graph"
      targets:
        - expr: "active_sessions_total"
```

## 🔄 Regular Security Tasks

### Daily
- [ ] Review security alerts
- [ ] Check failed authentication attempts
- [ ] Verify backup integrity

### Weekly
- [ ] Update dependencies
- [ ] Review access logs
- [ ] Test incident response procedures

### Monthly
- [ ] Rotate API keys
- [ ] Security vulnerability scan
- [ ] Review and update security policies
- [ ] Conduct security training

### Quarterly
- [ ] Penetration testing
- [ ] Security audit
- [ ] Disaster recovery testing
- [ ] Compliance assessment