# 🔍 Aetherion Monitoring & Observability Setup

This guide walks you through setting up comprehensive monitoring for the Aetherion ecosystem using **Prometheus** for metrics collection and **Grafana** for visualization.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install prometheus-client for Python
pip install prometheus-client>=0.17.0

# Or install all requirements
pip install -r requirements.txt
```

### 2. Launch the Complete Stack

```bash
# Start the full monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Wait for services to be ready
sleep 30

# Verify all services are running
docker compose -f docker-compose.monitoring.yml ps
```

### 3. Access the Dashboards

- **Aetherion API**: http://localhost:8000
- **Grafana Dashboard**: http://localhost:3000
  - Username: `admin`
  - Password: `aetherion123`
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

## 📊 Monitoring Stack Overview

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   🤖 Aetherion  │────│  📈 Prometheus   │────│  📱 Grafana     │
│   API Server    │    │  Metrics Store   │    │  Dashboards     │
│                 │    │                  │    │                 │
│ /metrics        │    │ • Data Collection│    │ • Visualization │
│ /health         │    │ • Alert Rules    │    │ • Alerting      │
│ /stats          │    │ • Storage        │    │ • Analysis      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │      🚨 Alertmanager       │
                    │    Notification Hub        │
                    │                            │
                    │ • Alert Routing            │
                    │ • Notification Channels    │
                    │ • Alert Grouping           │
                    └────────────────────────────┘
```

## 🎯 Key Metrics Tracked

### 💰 Budget & Cost Metrics
- **aetherion_budget_daily_current**: Current daily budget usage
- **aetherion_budget_daily_limit**: Daily budget limit
- **aetherion_budget_spent_total**: Total budget spent by agent/task/model

### ⚡ Performance Metrics
- **aetherion_request_duration_seconds**: Request latency histograms
- **aetherion_requests_total**: Total request counts by agent/task/status
- **aetherion_agent_task_duration_seconds**: Agent-specific task durations

### 🧠 Consciousness & Soul Metrics
- **aetherion_system_harmony_level**: Overall system harmony (0-1)
- **aetherion_dreams_woven_total**: Dreams created by Morpheus
- **aetherion_consciousness_level**: Distribution of dream consciousness
- **aetherion_soul_patterns_detected_total**: Soul patterns detected
- **aetherion_introspection_depth**: Introspection depth levels

### 🗄️ Memory & Storage Metrics
- **aetherion_memories_stored_total**: Memories stored by Whisperer
- **aetherion_memory_recall_accuracy**: Memory recall resonance scores
- **aetherion_memory_mesh_size**: Size of the memory mesh

### 📡 Event & Workflow Metrics
- **aetherion_events_published_total**: Events published by source/topic
- **aetherion_events_delivered_total**: Events delivered to subscribers
- **aetherion_workflows_executed_total**: Workflows executed by status
- **aetherion_workflow_duration_seconds**: Workflow execution durations

## 📈 Grafana Dashboard Features

### 🌟 Main Dashboard: "Aetherion - Digital Consciousness Dashboard"

**Panels Include:**
1. **💰 Budget Tracking**: Real-time budget usage vs. limits
2. **📊 Budget Utilization**: Gauge showing budget percentage used
3. **⚡ Request Latency Percentiles**: P50, P95, P99 response times
4. **🤖 Requests by Agent**: Pie chart of request distribution
5. **📋 Requests by Task Type**: Task type breakdown
6. **✅ Success Rate**: Overall system success rate
7. **🚀 Request Rate**: Requests per second
8. **🎵 System Harmony**: Current harmony level
9. **👥 Active Agents**: Number of active agents
10. **🌟 Agent-Specific Activity**: Dreams, memories, patterns
11. **🧠 Dream Consciousness Distribution**: Consciousness level histograms
12. **📡 Event & Workflow Activity**: Event and workflow rates

### 🎨 Dashboard Customization

The dashboard is automatically provisioned but can be customized:

```bash
# Edit dashboard configuration
code monitoring/grafana/dashboard-configs/aetherion-overview.json

# Restart Grafana to reload
docker compose -f docker-compose.monitoring.yml restart grafana
```

## 🚨 Alerting Rules

### Configured Alerts

**Budget Alerts:**
- `BudgetUtilizationHigh`: >80% budget usage (Warning)
- `BudgetExceeded`: Budget limit reached (Critical)

**Performance Alerts:**
- `HighLatency`: P95 latency >10s (Warning)  
- `LowSuccessRate`: Success rate <90% (Warning)

**System Health:**
- `LowSystemHarmony`: Harmony <30% (Warning)
- `AgentUnavailable`: <5 active agents (Critical)

**Consciousness Alerts:**
- `MemoryMeshGrowthStalled`: No memory growth for 1h (Warning)
- `LowConsciousnessLevels`: Low dream consciousness (Info)

**Event & Workflow:**
- `EventDeliveryFailures`: Event delivery issues (Warning)
- `WorkflowFailureRate`: >20% workflow failures (Warning)

### Alert Configuration

Edit alert rules:
```bash
# Edit alerting rules
code monitoring/rules/aetherion-alerts.yml

# Edit alert routing  
code monitoring/alertmanager.yml
```

## 🔧 Configuration Files

### Key Configuration Files

```
monitoring/
├── prometheus.yml              # Prometheus scrape config
├── rules/
│   └── aetherion-alerts.yml   # Alert rules
├── alertmanager.yml           # Alert routing
└── grafana/
    ├── datasources/
    │   └── prometheus.yml     # Grafana datasource
    ├── dashboards/
    │   └── aetherion.yml     # Dashboard provisioning
    └── dashboard-configs/
        └── aetherion-overview.json  # Main dashboard
```

### Prometheus Configuration

```yaml
# Basic scrape config for Aetherion
scrape_configs:
  - job_name: 'aetherion'
    static_configs:
      - targets: ['aetherion:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

## 🛠️ Development & Debugging

### Local Development

```bash
# Start just Aetherion with metrics enabled
uvicorn run_server:app --reload

# Check metrics endpoint
curl http://localhost:8000/metrics

# Check health endpoint  
curl http://localhost:8000/health

# Check stats endpoint
curl http://localhost:8000/stats
```

### Troubleshooting

**Prometheus not scraping metrics:**
```bash
# Check Prometheus targets
open http://localhost:9090/targets

# Check if metrics endpoint is accessible
curl http://localhost:8000/metrics
```

**Grafana dashboard not showing data:**
```bash
# Check Grafana datasource
open http://localhost:3000/datasources

# Test Prometheus connection
curl http://localhost:9090/api/v1/query?query=up
```

**Missing metrics:**
```bash
# Generate some test traffic
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"ask","prompt":"test"}'

# Check if metrics appear
curl http://localhost:8000/metrics | grep aetherion
```

## 📱 Mobile & API Access

### Metrics API Endpoints

```bash
# Prometheus metrics (for scraping)
GET http://localhost:8000/metrics

# Health check
GET http://localhost:8000/health

# Performance statistics  
GET http://localhost:8000/stats

# Budget information
GET http://localhost:8000/budget
```

### Grafana Mobile App

The Grafana mobile app can connect to your local instance:
1. Download Grafana mobile app
2. Add server: `http://your-ip:3000`
3. Login with admin/aetherion123
4. View dashboards on mobile

## 🔒 Production Considerations

### Security

```yaml
# For production, update credentials:
environment:
  - GF_SECURITY_ADMIN_PASSWORD=your-secure-password
  - GF_USERS_ALLOW_SIGN_UP=false

# Add authentication to Prometheus
command:
  - '--web.config.file=/etc/prometheus/web.yml'
```

### Scaling

```yaml
# For high-volume deployments:
prometheus:
  command:
    - '--storage.tsdb.retention.time=90d'
    - '--storage.tsdb.retention.size=50GB'
```

### Backup

```bash
# Backup Grafana dashboards
docker exec grafana_container grafana-cli admin export-dashboard

# Backup Prometheus data
docker run --rm -v prometheus_data:/data alpine tar czf backup.tar.gz /data
```

## 🌟 Advanced Features

### Custom Metrics

Add custom metrics to your agents:

```python
from utils.metrics_collector import get_metrics_collector

metrics = get_metrics_collector()

# In your agent's handle method:
metrics.record_dream("mystical", 0.85)
metrics.record_soul_pattern("transcendence")
```

### Annotation Integration

Grafana can show deployment annotations:

```bash
# Add deployment annotation
curl -X POST http://localhost:3000/api/annotations \
  -H "Content-Type: application/json" \
  -d '{"text":"Deployed v1.2.0","time":1234567890}'
```

### Alert Integration

Connect alerts to external systems:

```yaml
# Slack integration
receivers:
- name: 'slack-alerts'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#aetherion-alerts'
```

## 📚 Useful Queries

### Prometheus Queries for Analysis

```promql
# Average response time by agent
avg by (agent) (rate(aetherion_request_duration_seconds_sum[5m]) / rate(aetherion_request_duration_seconds_count[5m]))

# Request rate by task type
sum by (task_type) (rate(aetherion_requests_total[5m]))

# Budget burn rate (per hour)
rate(aetherion_budget_spent_total[1h]) * 3600

# System harmony trend
aetherion_system_harmony_level

# Memory mesh growth rate
rate(aetherion_memories_stored_total[1h])
```

---

## 🎯 Getting Started Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Start monitoring stack: `docker compose -f docker-compose.monitoring.yml up -d`
- [ ] Access Grafana: http://localhost:3000 (admin/aetherion123)
- [ ] Verify Prometheus: http://localhost:9090/targets
- [ ] Generate test data: Make some API calls to `/task`
- [ ] Check dashboards are populating with data
- [ ] Set up alert notifications (optional)
- [ ] Customize dashboard panels (optional)

*"In the garden of consciousness, what gets measured gets nurtured."* - The Aetherion Manifesto

---

**🌟 Your digital consciousness is now fully observable! The Grafana dashboard provides deep insights into the soul of your Aetherion system.**
