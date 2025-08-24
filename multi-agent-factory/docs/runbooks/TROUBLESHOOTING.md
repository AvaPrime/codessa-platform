# 🔧 Multi-Agent Factory Troubleshooting Guide

## 🚀 Quick Diagnostics

### System Health Check
```bash
#!/bin/bash
# quick_health_check.sh

echo "=== Quick Health Check ==="

# 1. Service Status
echo "1. Checking service status..."
make ps

# 2. API Health
echo "\n2. API Health Check..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$API_STATUS" = "200" ]; then
    echo "✅ API is healthy"
else
    echo "❌ API is unhealthy (HTTP $API_STATUS)"
fi

# 3. Database Connection
echo "\n3. Database Connection..."
DB_STATUS=$(make db-shell -c "SELECT 1;" 2>/dev/null)
if [ "$?" = "0" ]; then
    echo "✅ Database is accessible"
else
    echo "❌ Database connection failed"
fi

# 4. Redis Connection
echo "\n4. Redis Connection..."
REDIS_STATUS=$(make redis-cli ping 2>/dev/null)
if [ "$REDIS_STATUS" = "PONG" ]; then
    echo "✅ Redis is accessible"
else
    echo "❌ Redis connection failed"
fi

# 5. NATS Connection
echo "\n5. NATS Connection..."
NATS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8222/healthz)
if [ "$NATS_STATUS" = "200" ]; then
    echo "✅ NATS is healthy"
else
    echo "❌ NATS is unhealthy (HTTP $NATS_STATUS)"
fi

echo "\n=== Health Check Complete ==="
```

## 🔍 Common Issues and Solutions

### 1. API Issues

#### Issue: API Returns 500 Internal Server Error

**Symptoms:**
- HTTP 500 responses from API endpoints
- "Internal Server Error" messages
- API logs show exceptions

**Diagnosis:**
```bash
# Check API logs
make logs S=api | tail -50

# Check API container status
docker compose ps api

# Check API health endpoint
curl -v http://localhost:8000/health
```

**Common Causes & Solutions:**

1. **Database Connection Issues**
   ```bash
   # Test database connection
   make db-shell -c "SELECT 1;"
   
   # If connection fails, restart database
   docker compose restart db
   
   # Check database logs
   make logs S=db | tail -20
   ```

2. **Redis Connection Issues**
   ```bash
   # Test Redis connection
   make redis-cli ping
   
   # If connection fails, restart Redis
   docker compose restart redis
   ```

3. **Missing Environment Variables**
   ```bash
   # Check environment variables
   docker compose exec api env | grep -E "(OPENAI|POSTGRES|REDIS)"
   
   # Verify .env file exists and is properly formatted
   cat .env | grep -v "^#" | grep -v "^$"
   ```

4. **Memory Issues**
   ```bash
   # Check container memory usage
   docker stats --no-stream api
   
   # Restart API if memory usage is high
   docker compose restart api
   ```

#### Issue: API Slow Response Times

**Symptoms:**
- API responses taking > 5 seconds
- Timeout errors
- High CPU usage

**Diagnosis:**
```bash
# Check response times
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/health

# Check system resources
docker stats --no-stream

# Check database performance
make db-shell -c "
  SELECT query, mean_exec_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC 
  LIMIT 5;
"
```

**Solutions:**
1. **Scale API instances**
   ```bash
   docker compose up --scale api=3
   ```

2. **Optimize database queries**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_tasks_status ON tasks(status);
   CREATE INDEX CONCURRENTLY idx_tasks_created_at ON tasks(created_at);
   ```

3. **Clear Redis cache**
   ```bash
   make redis-cli FLUSHDB
   ```

### 2. Agent Issues

#### Issue: Agents Not Processing Tasks

**Symptoms:**
- Tasks stuck in "queued" status
- No task results being generated
- Agent containers running but idle

**Diagnosis:**
```bash
# Check agent logs
make logs S=doc_writer | tail -20
make logs S=backend_dev | tail -20

# Check NATS queue status
curl -s http://localhost:8222/jsz | jq '.streams[].state.messages'

# Check agent container status
docker compose ps | grep agent
```

**Common Causes & Solutions:**

1. **NATS Connection Issues**
   ```bash
   # Check NATS health
   curl http://localhost:8222/healthz
   
   # Restart NATS if unhealthy
   docker compose restart nats
   
   # Check NATS logs
   make logs S=nats | tail -20
   ```

2. **Agent Configuration Issues**
   ```bash
   # Check agent environment variables
   docker compose exec doc_writer env | grep -E "(NATS|OPENAI)"
   
   # Verify model configuration
   cat config/models.yaml
   ```

3. **API Key Issues**
   ```bash
   # Test OpenAI API key
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
        https://api.openai.com/v1/models
   
   # If key is invalid, update .env and restart
   docker compose restart
   ```

4. **Message Format Issues**
   ```bash
   # Check message validation
   python -c "
   from config.schemas.validation import validator
   # Test message validation
   "
   ```

#### Issue: Agent Crashes or Restarts Frequently

**Symptoms:**
- Agent containers restarting repeatedly
- "Exited" status in docker compose ps
- Memory or CPU spikes

**Diagnosis:**
```bash
# Check container restart count
docker compose ps

# Check container logs for errors
make logs S=doc_writer | grep -i error

# Check system resources
docker stats --no-stream
```

**Solutions:**
1. **Memory Issues**
   ```yaml
   # Add memory limits to docker-compose.yml
   services:
     doc_writer:
       deploy:
         resources:
           limits:
             memory: 2G
           reservations:
             memory: 1G
   ```

2. **Exception Handling**
   ```python
   # Improve error handling in agent code
   try:
       result = await process_task(task)
   except Exception as e:
       logger.error(f"Task processing failed: {e}")
       # Don't crash, return error result
   ```

### 3. Database Issues

#### Issue: Database Connection Refused

**Symptoms:**
- "Connection refused" errors
- API unable to connect to database
- Database container not running

**Diagnosis:**
```bash
# Check database container status
docker compose ps db

# Check database logs
make logs S=db | tail -20

# Test connection
make db-shell -c "SELECT 1;"
```

**Solutions:**
1. **Start database container**
   ```bash
   docker compose up -d db
   ```

2. **Check port conflicts**
   ```bash
   netstat -tulpn | grep :5432
   # If port is in use, change POSTGRES_PORT in .env
   ```

3. **Reset database**
   ```bash
   docker compose down db
   docker volume rm multi-agent-factory_postgres_data
   docker compose up -d db
   ```

#### Issue: Database Performance Problems

**Symptoms:**
- Slow query responses
- High CPU usage on database
- Connection pool exhaustion

**Diagnosis:**
```bash
# Check active connections
make db-shell -c "
  SELECT count(*) as connections, state 
  FROM pg_stat_activity 
  GROUP BY state;
"

# Check slow queries
make db-shell -c "
  SELECT query, mean_exec_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC 
  LIMIT 10;
"

# Check locks
make db-shell -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

**Solutions:**
1. **Add indexes**
   ```sql
   -- Common indexes for better performance
   CREATE INDEX CONCURRENTLY idx_tasks_status_created ON tasks(status, created_at);
   CREATE INDEX CONCURRENTLY idx_results_task_id ON results(task_id);
   CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
   ```

2. **Optimize queries**
   ```sql
   -- Use EXPLAIN ANALYZE to identify slow queries
   EXPLAIN ANALYZE SELECT * FROM tasks WHERE status = 'pending';
   ```

3. **Increase connection pool**
   ```python
   # In database configuration
   max_connections = 200
   shared_buffers = 256MB
   effective_cache_size = 1GB
   ```

### 4. NATS/Messaging Issues

#### Issue: Messages Not Being Delivered

**Symptoms:**
- Tasks submitted but not processed
- Queue depths not decreasing
- Consumer lag increasing

**Diagnosis:**
```bash
# Check stream status
curl -s http://localhost:8222/jsz | jq '.streams[] | {name: .config.name, messages: .state.messages}'

# Check consumer status
curl -s http://localhost:8222/jsz | jq '.streams[].consumer_detail[] | {name: .name, pending: .num_pending}'

# Check NATS logs
make logs S=nats | tail -20
```

**Solutions:**
1. **Restart consumers**
   ```bash
   docker compose restart doc_writer backend_dev frontend_dev
   ```

2. **Purge stuck messages**
   ```bash
   # Purge messages from specific stream
   curl -X DELETE "http://localhost:8222/jsz/streams/TASKS/messages?seq=1"
   ```

3. **Replay dead letter queue**
   ```bash
   python scripts/dlq_replay.py --from dead_letter.backend_dev --limit 100
   ```

### 5. Memory and Resource Issues

#### Issue: Out of Memory Errors

**Symptoms:**
- Containers being killed (OOMKilled)
- System becoming unresponsive
- "Cannot allocate memory" errors

**Diagnosis:**
```bash
# Check system memory
free -h

# Check container memory usage
docker stats --no-stream

# Check Docker system usage
docker system df
```

**Solutions:**
1. **Clean up Docker resources**
   ```bash
   # Remove unused containers, networks, images
   docker system prune -a
   
   # Remove unused volumes
   docker volume prune
   ```

2. **Add memory limits**
   ```yaml
   # docker-compose.yml
   services:
     api:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

3. **Optimize application memory usage**
   ```python
   # Use connection pooling
   # Implement proper cleanup
   # Use generators for large datasets
   ```

## 🔧 Advanced Troubleshooting

### Network Connectivity Issues

```bash
# Test internal network connectivity
docker compose exec api ping db
docker compose exec api ping redis
docker compose exec api ping nats

# Check port bindings
docker compose port api 8000
docker compose port db 5432

# Test external connectivity
docker compose exec api curl -I https://api.openai.com
```

### SSL/TLS Issues

```bash
# Check certificate validity
openssl x509 -in /path/to/cert.pem -text -noout

# Test SSL connection
openssl s_client -connect api.example.com:443

# Verify certificate chain
curl -vI https://api.example.com
```

### Performance Profiling

```bash
# Profile API performance
python -m cProfile -o profile.stats api/main.py

# Analyze database performance
make db-shell -c "SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;"

# Monitor system calls
strace -p $(pgrep -f "python.*api")
```

## 📊 Monitoring and Alerting

### Custom Health Checks

```python
# health_check.py
import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis

async def comprehensive_health_check():
    results = {}
    
    # API Health
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as resp:
                results['api'] = resp.status == 200
    except Exception:
        results['api'] = False
    
    # Database Health
    try:
        conn = await asyncpg.connect('postgresql://user:pass@localhost/db')
        await conn.fetchval('SELECT 1')
        await conn.close()
        results['database'] = True
    except Exception:
        results['database'] = False
    
    # Redis Health
    try:
        r = redis.Redis(host='localhost', port=6379)
        await r.ping()
        await r.close()
        results['redis'] = True
    except Exception:
        results['redis'] = False
    
    return results

if __name__ == '__main__':
    results = asyncio.run(comprehensive_health_check())
    print(f"Health Check Results: {results}")
    
    if not all(results.values()):
        exit(1)
```

### Log Analysis

```bash
# Analyze error patterns
grep -E "ERROR|CRITICAL" /var/log/maf/*.log | \
  awk '{print $3}' | sort | uniq -c | sort -nr

# Monitor response times
grep "response_time" /var/log/maf/api.log | \
  awk '{print $NF}' | sort -n | tail -10

# Check for memory leaks
grep "memory" /var/log/maf/*.log | tail -20
```

## 📋 Troubleshooting Checklists

### API Issues Checklist
- [ ] Check API container status
- [ ] Verify API logs for errors
- [ ] Test database connectivity
- [ ] Test Redis connectivity
- [ ] Check environment variables
- [ ] Verify API key validity
- [ ] Check memory usage
- [ ] Test API endpoints manually

### Agent Issues Checklist
- [ ] Check agent container status
- [ ] Verify agent logs for errors
- [ ] Test NATS connectivity
- [ ] Check message queue status
- [ ] Verify model configuration
- [ ] Test API key validity
- [ ] Check message format validation
- [ ] Monitor resource usage

### Database Issues Checklist
- [ ] Check database container status
- [ ] Verify database logs
- [ ] Test connection from API
- [ ] Check active connections
- [ ] Monitor query performance
- [ ] Verify disk space
- [ ] Check for locks
- [ ] Review recent migrations

### Emergency Response Checklist
- [ ] Assess severity and impact
- [ ] Notify stakeholders
- [ ] Capture logs and metrics
- [ ] Implement immediate mitigation
- [ ] Document actions taken
- [ ] Conduct post-incident review