---
title: Incident Response Runbook
owner: DevOps Team
version: 1.0
last_reviewed: 2025-01-20
next_review: 2025-04-20
status: operational
---

# Incident Response Runbook

## 🚨 Emergency Contacts

### Primary Contacts
- **On-Call Engineer**: +1-555-ON-CALL
- **Team Lead**: lead@company.com
- **DevOps Team**: devops@company.com
- **Security Team**: security@company.com

### Communication Channels
- **Alerts**: #maf-alerts
- **Incidents**: #incidents
- **General**: #maf-team
- **Status Page**: https://status.company.com

## 📊 Severity Classification

### P0 - Critical (System Down)
**Response Time: Immediate (< 5 minutes)**
- Complete system outage
- Data corruption or loss
- Security breach
- Customer-facing services unavailable

**Actions:**
1. Page on-call engineer immediately
2. Create incident channel: #incident-YYYY-MM-DD-NNN
3. Notify leadership within 15 minutes
4. Update status page
5. Begin immediate mitigation

### P1 - High (Major Feature Down)
**Response Time: 15 minutes**
- API returning 5xx errors (>5% error rate)
- Critical agents not processing tasks
- Database connectivity issues
- Authentication system down

**Actions:**
1. Notify on-call engineer
2. Create incident channel
3. Begin investigation
4. Update status page if customer-facing

### P2 - Medium (Performance Degraded)
**Response Time: 1 hour**
- Slow response times (>2x normal)
- High resource usage (>80%)
- Non-critical feature issues
- Queue backlogs

**Actions:**
1. Create incident ticket
2. Assign to appropriate team member
3. Monitor for escalation

### P3 - Low (Minor Issues)
**Response Time: Next business day**
- Cosmetic issues
- Documentation problems
- Non-urgent feature requests

**Actions:**
1. Create backlog item
2. Schedule for next sprint

## 🔥 Incident Response Process

### Phase 1: Detection & Alert (0-5 minutes)

#### Automated Detection
- Monitoring alerts (Prometheus/Grafana)
- Health check failures
- Error rate thresholds
- Performance degradation

#### Manual Detection
- Customer reports
- Team member observations
- Third-party service notifications

#### Initial Response
```bash
# Quick assessment
make verify
make ps
docker stats --no-stream

# Check key services
curl -f http://localhost:8000/health
curl -f http://localhost:8222/varz
make db-shell -c "SELECT 1;"
make redis-cli ping
```

### Phase 2: Triage & Classification (5-15 minutes)

#### Severity Assessment
1. **Impact**: How many users/systems affected?
2. **Urgency**: How quickly must this be resolved?
3. **Scope**: Is this isolated or widespread?
4. **Trend**: Is it getting worse?

#### Incident Declaration
```bash
# Create incident channel
/incident create "Brief description of the issue"

# Set severity
/incident severity P1

# Assign incident commander
/incident assign @username
```

#### Communication Template
🚨 INCIDENT DECLARED 🚨

Severity: P1
Title: [Brief description]
Start Time: [YYYY-MM-DD HH:MM UTC]
Incident Commander: @username

Initial Assessment:

- Impact: [Description]
- Affected Services: [List]
- Current Status: [Investigating/Mitigating]
Next Update: [Time]

### Phase 3: Investigation & Mitigation (15 minutes - 4 hours)

#### Investigation Checklist
- [ ] Check recent deployments/changes
- [ ] Review monitoring dashboards
- [ ] Analyze error logs
- [ ] Check external dependencies
- [ ] Verify infrastructure status
- [ ] Review resource utilization

#### Common Investigation Commands
```bash
# Recent deployments
git log --oneline --since="2 hours ago"

# System resources
df -h
free -m
docker system df

# Service logs
make logs S=api | tail -100
make logs S=nats | grep ERROR

# Database status
make db-shell -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
  FROM pg_stat_activity 
  WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
"

# NATS status
curl -s http://localhost:8222/jsz | jq '.streams[].state'

# Redis status
make redis-cli info memory
```

#### Mitigation Strategies

**Service Recovery**
```bash
# Restart specific service
docker-compose restart api

# Scale up replicas
docker-compose up --scale api=3

# Rollback deployment
git revert HEAD
make deploy

# Emergency maintenance mode
echo "maintenance" > /var/www/html/maintenance.html
```

**Database Issues**
```bash
# Kill long-running queries
make db-shell -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '10 minutes';"

# Restart database (last resort)
docker-compose restart db
```

**Queue Management**
```bash
# Purge problematic queues
curl -X DELETE http://localhost:8222/jsz/streams/TASKS/messages

# Replay dead letter queue
python scripts/dlq_replay.py --from dead_letter.backend_dev --limit 100
```

### Phase 4: Communication & Updates

#### Update Frequency
- **P0**: Every 15 minutes
- **P1**: Every 30 minutes
- **P2**: Every 2 hours
- **P3**: Daily

#### Update Template

