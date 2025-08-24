# Multi-Agent Factory Docker Configuration

This directory contains the Docker configuration for the Multi-Agent Factory system, including enhanced agent containers with security, monitoring, and operational best practices.

## 🏗️ Architecture Overview

The Docker setup consists of:

- **agent.Dockerfile**: Multi-stage build for secure, optimized agent containers
- **docker-compose.yml**: Core infrastructure and basic agent services
- **docker-compose.agents.yml**: Enhanced agent services with resource management
- **docker-compose.security.yml**: Security-hardened configuration
- **agent-entrypoint.sh**: Advanced agent initialization and health management

## 🚀 Quick Start

### Basic Setup

```bash
# Start core infrastructure and basic agents
docker compose up -d

# View logs
docker compose logs -f

# Scale specific agents
docker compose up --scale doc-writer=3 -d
```

### Enhanced Agent Setup

```bash
# Start with enhanced agent configuration
docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d

# Start with observability stack
docker compose --profile obs up -d

# Start with security hardening
docker compose -f docker-compose.yml -f docker-compose.security.yml up -d
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp ../../.env.example ../../.env
# Edit .env with your configuration
```

### Secrets Management

Secrets are stored in `./secrets/` directory:

- `openai_api_key.txt` - OpenAI API key
- `jwt_secret.txt` - JWT signing secret
- `encryption_key.txt` - Data encryption key

**⚠️ Security Note**: Never commit actual secrets to version control.

### Agent Configuration

Each agent can be configured with:

```yaml
environment:
  AGENT_ROLE: doc_writer
  MAX_CONCURRENT_TASKS: 3
  TASK_TIMEOUT: 300
  DEBUG: false
```

## 🏗️ Agent.Dockerfile Features

### Multi-Stage Build

1. **Builder Stage**: Compiles Python wheels with build dependencies
2. **Runtime Stage**: Minimal runtime environment with security hardening

### Security Features

- ✅ Non-root user execution
- ✅ Minimal attack surface
- ✅ Security updates applied
- ✅ Read-only filesystem support
- ✅ Resource constraints
- ✅ Health checks enabled

### Operational Features

- 🔍 Enhanced health checks with JSON output
- 📊 Built-in metrics and monitoring
- 🔄 Graceful shutdown handling
- 📝 Structured logging
- 🚨 Dependency validation
- ⚡ Fast startup with pre-built wheels

## 🎯 Agent Services

### Core Agents

| Agent | Purpose | Resources | Scaling |
|-------|---------|-----------|----------|
| `doc-writer` | Documentation generation | 512MB/0.5 CPU | Horizontal |
| `frontend-dev` | Frontend development | 1GB/1.0 CPU | Limited |
| `backend-dev` | Backend development | 1GB/1.0 CPU | Limited |
| `compliance-checker` | Security compliance | 256MB/0.3 CPU | Horizontal |
| `qa-tester` | Quality assurance | 512MB/0.5 CPU | Horizontal |

### Enhanced Agents (docker-compose.agents.yml)

| Agent | Purpose | Resources | Features |
|-------|---------|-----------|----------|
| `data-analyst` | Data analysis | 512MB/0.5 CPU | Analytics |
| `security-auditor` | Security scanning | 256MB/0.3 CPU | Compliance |
| `performance-monitor` | System monitoring | 128MB/0.2 CPU | Metrics |

## 🔍 Monitoring & Health Checks

### Health Endpoints

Each agent exposes health endpoints:

- `GET /health` - Detailed health status (JSON)
- `GET /ready` - Readiness check (text)

### Health Check Response

```json
{
  "status": "healthy",
  "agent_role": "doc_writer",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime": 3600.5,
  "environment": "prod"
}
```

### Monitoring Stack

With `--profile obs`:

- **Prometheus**: Metrics collection (`:9090`)
- **Grafana**: Dashboards (`:3000`)
- **Jaeger**: Distributed tracing (`:16686`)

## 🔒 Security

### Container Security

- Non-privileged execution
- Read-only root filesystem
- No new privileges
- Security options enabled
- Minimal base image

### Network Security

- Internal networks for agent communication
- TLS encryption for external connections
- Network policies for isolation

### Secrets Management

- Docker secrets for sensitive data
- Environment variable isolation
- Encrypted storage volumes

## 🚀 Deployment

### Development

```bash
# Development with hot reload
docker compose --profile dev up -d

# View specific agent logs
docker compose logs -f doc-writer

# Execute commands in agent container
docker compose exec doc-writer bash
```

### Production

```bash
# Production deployment
docker compose -f docker-compose.yml -f docker-compose.security.yml up -d

# Health check all services
docker compose ps

# Update specific agent
docker compose up -d --no-deps doc-writer
```

### Scaling

```bash
# Scale horizontally
docker compose up --scale doc-writer=5 --scale qa-tester=3 -d

# Auto-scaling with resource limits
docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d
```

## 🛠️ Troubleshooting

### Common Issues

#### Agent Won't Start

```bash
# Check agent logs
docker compose logs doc-writer

# Check dependencies
docker compose ps

# Validate configuration
docker compose config
```

#### Health Check Failures

```bash
# Manual health check
curl http://localhost:8080/health

# Check agent status
docker compose exec doc-writer python -c "import agents.doc_writer.agent"
```

#### Resource Issues

```bash
# Check resource usage
docker stats

# Adjust resource limits in docker-compose.agents.yml
# Restart affected services
docker compose restart doc-writer
```

### Debug Mode

Enable debug mode:

```bash
# Set in .env
DEBUG=true

# Or override for specific agent
docker compose run -e DEBUG=true doc-writer
```

## 📊 Performance Tuning

### Resource Optimization

1. **Memory**: Adjust based on agent workload
2. **CPU**: Scale based on processing requirements
3. **I/O**: Use volume mounts for persistent data
4. **Network**: Optimize for agent communication patterns

### Scaling Strategies

1. **Horizontal**: Multiple instances of stateless agents
2. **Vertical**: Increase resources for compute-intensive agents
3. **Hybrid**: Combine both approaches based on agent characteristics

## 🔄 Maintenance

### Updates

```bash
# Update base images
docker compose pull

# Rebuild agent images
docker compose build --no-cache

# Rolling update
docker compose up -d --force-recreate
```

### Cleanup

```bash
# Remove stopped containers
docker compose down

# Clean up volumes (⚠️ data loss)
docker compose down -v

# Clean up images
docker image prune -f
```

### Backup

```bash
# Backup volumes
docker run --rm -v maf_dbdata:/data -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz -C /data .

# Backup configuration
tar czf config-backup.tar.gz .env secrets/ docker-compose*.yml
```

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Multi-Agent Factory Documentation](../../docs/)
- [Security Best Practices](../../docs/SECURITY.md)
- [Deployment Guide](../../docs/DEPLOYMENT.md)

## 🤝 Contributing

When adding new agents:

1. Create agent directory in `agents/`
2. Add service definition to `docker-compose.agents.yml`
3. Update this README with agent documentation
4. Test with `docker compose config`
5. Submit PR with comprehensive testing

---

**Note**: This configuration follows security best practices and operational excellence patterns. Always review and adapt to your specific requirements.