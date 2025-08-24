---
title: Incident Response Runbook
owner: DevOps Team
version: 1.0
last_reviewed: 2025-01-15
next_review: 2025-04-15
status: operational
---

# 🚨 Incident Response Runbook

## 📞 Emergency Contacts
- **On-Call Engineer**: [Slack: @oncall] [Phone: +1-xxx-xxx-xxxx]
- **Engineering Manager**: [Slack: @eng-manager] [Phone: +1-xxx-xxx-xxxx]
- **DevOps Lead**: [Slack: @devops-lead] [Phone: +1-xxx-xxx-xxxx]

## 🎯 Severity Levels

### P0 - Critical (Response: Immediate)
- Complete system outage
- Data loss or corruption
- Security breach
- SLA breach affecting all customers

### P1 - High (Response: 15 minutes)
- Partial system outage
- Significant performance degradation
- Single agent type completely down
- API error rate > 5%

### P2 - Medium (Response: 1 hour)
- Minor performance issues
- Non-critical feature unavailable
- Individual agent instances failing
- Monitoring alerts

### P3 - Low (Response: Next business day)
- Cosmetic issues
- Documentation problems
- Non-urgent improvements

## 🔥 Incident Response Process

### 1. Detection and Alert
```bash
# Immediate health check
make verify
make curl
make nats-health

# Check system status
make ps
docker compose ps
```

### 2. Initial Assessment (5 minutes)
```bash
# Check recent deployments
git log --oneline -10

# Review recent logs
make logs | tail -100

# Check resource usage
docker stats
```

### 3. Communication
- **Slack**: Post in #incidents channel
- **Status Page**: Update if customer-facing
- **Stakeholders**: Notify based on severity

### 4. Investigation and Mitigation

#### API Issues
```bash
# Check API health
curl -v http://localhost:8000/health

# Review API logs
docker compose logs api

# Check database connectivity
make db-shell
\l  # List databases
\dt # List tables
```

#### Agent Issues
```bash
# Check agent status
make agent-status

# Review specific agent logs
docker compose logs doc-writer
docker compose logs frontend-dev

# Check NATS connectivity
make nats-health
curl http://localhost:8222/varz
```

#### Database Issues
```bash
# Check PostgreSQL status
docker compose exec db pg_isready

# Monitor connections
docker compose exec db psql -U user -d factory -c "SELECT * FROM pg_stat_activity;"

# Check disk space
docker compose exec db df -h
```

#### Message Queue Issues
```bash
# NATS monitoring
curl http://localhost:8222/healthz
curl http://localhost:8222/varz | jq

# Check JetStream status
curl http://localhost:8222/jsz | jq

# List streams and consumers
nats stream ls
nats consumer ls
```

### 5. Resolution Actions

#### Quick Fixes
```bash
# Restart all services
make down && make up

# Restart specific service
docker compose restart api
docker compose restart doc-writer

# Clear Redis cache
make redis-cli
FLUSHALL

# Replay DLQ messages
python scripts/dlq_replay.py --from dead_letter.backend_dev
```

#### Rollback Procedures
```bash
# Git rollback
git revert HEAD
git push origin main

# Docker image rollback
docker compose down
docker compose pull
docker compose up -d

# Database rollback
alembic downgrade -1
```

## 📊 Common Incident Scenarios

### Scenario 1: High API Latency
**Symptoms**: API p95 > 300ms, timeout errors

**Investigation**:
```bash
# Check database performance
make db-shell
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;

# Check Redis performance
make redis-cli
INFO stats

# Review slow queries
tail -f /var/log/postgresql/postgresql.log | grep "slow query"
```

**Resolution**:
1. Scale API instances: `docker compose up --scale api=3`
2. Clear Redis cache if stale
3. Optimize slow queries
4. Add database indexes if needed

### Scenario 2: Agent Not Processing Tasks
**Symptoms**: Tasks stuck in queue, no agent responses

**Investigation**:
```bash
# Check agent health
curl http://localhost:8000/agents

# Verify NATS subjects
nats sub "tasks.>" --count=10

# Check DLQ
nats stream info TASKS
```

**Resolution**:
1. Restart affected agents
2. Check agent configuration
3. Verify NATS connectivity
4. Replay failed messages from DLQ

### Scenario 3: Database Connection Issues
**Symptoms**: Connection refused, pool exhaustion

**Investigation**:
```bash
# Check connection limits
make db-shell
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;

# Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

**Resolution**:
1. Kill long-running queries
2. Restart database if needed
3. Adjust connection pool settings
4. Scale database if persistent

### Scenario 4: Memory/Disk Space Issues
**Symptoms**: OOM kills, disk full errors

**Investigation**:
```bash
# Check disk usage
df -h
docker system df

# Check memory usage
free -h
docker stats

# Check log sizes
du -sh /var/lib/docker/containers/*/*-json.log
```

**Resolution**:
1. Clean up Docker: `docker system prune -af`
2. Rotate logs: `docker compose logs --tail=0`
3. Scale down non-essential services
4. Add more resources if needed

## 🔄 Post-Incident Process

### 1. Resolution Confirmation
- [ ] All systems operational
- [ ] Metrics back to normal
- [ ] No error alerts
- [ ] Customer impact resolved

### 2. Communication
- [ ] Update incident channel
- [ ] Notify stakeholders
- [ ] Update status page
- [ ] Send resolution summary

### 3. Post-Mortem (Within 48 hours)
- [ ] Timeline of events
- [ ] Root cause analysis
- [ ] Action items identified
- [ ] Prevention measures
- [ ] Documentation updates

## 📋 Incident Template