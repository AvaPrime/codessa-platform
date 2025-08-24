# Multi-Agent Factory Kubernetes Infrastructure

This directory contains the complete Kubernetes infrastructure configuration for the Multi-Agent Factory (MAF) platform. The infrastructure is designed for production-grade deployment with high availability, scalability, security, and observability.

## 🏗️ Architecture Overview

The MAF Kubernetes infrastructure consists of the following components:

### Core Services
- **PostgreSQL Database**: Primary data store with high availability
- **Redis Cache**: In-memory caching and session storage
- **NATS Messaging**: Event-driven communication between agents
- **MAF API**: RESTful API server for agent orchestration
- **Agent Workers**: Specialized AI agents for different tasks

### Infrastructure Services
- **Ingress Controller**: NGINX-based load balancing and SSL termination
- **Monitoring Stack**: Prometheus, Grafana, and Jaeger for observability
- **Logging Stack**: Fluent Bit, Elasticsearch, and Kibana for centralized logging
- **Security**: Pod Security Standards, Network Policies, and security scanning
- **Backup & Recovery**: Automated backups and disaster recovery procedures

## 📁 File Structure

```
infra/k8s/
├── 01-secrets.yaml              # Kubernetes Secrets for sensitive data
├── 02-storage.yaml              # Storage Classes and Persistent Volume Claims
├── 03-database.yaml             # PostgreSQL database deployment
├── 04-redis.yaml                # Redis cache deployment
├── 05-nats.yaml                 # NATS messaging system
├── 06-api.yaml                  # MAF API server deployment
├── 07-agents.yaml               # AI agent worker deployments
├── 08-ingress.yaml              # Ingress configuration and load balancing
├── 09-monitoring.yaml           # Prometheus, Grafana, and Jaeger
├── 10-autoscaling.yaml          # HPA, VPA, and resource management
├── 11-network-policies.yaml     # Network security policies
├── 12-backup-recovery.yaml      # Backup jobs and disaster recovery
├── 13-security.yaml             # Security policies and scanning
├── 14-logging-observability.yaml # Centralized logging and observability
├── deploy.sh                    # Deployment automation script
├── generate-secrets.sh          # Secret generation utility
└── README.md                    # This documentation
```

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster**: v1.25+ with at least 3 nodes
2. **kubectl**: Configured to access your cluster
3. **Helm**: v3.0+ for package management
4. **Storage**: Dynamic provisioning with SSD storage class
5. **Ingress Controller**: NGINX Ingress Controller (auto-installed if missing)

### Minimum Resource Requirements

- **CPU**: 8 cores total
- **Memory**: 16GB RAM total
- **Storage**: 500GB SSD storage
- **Network**: CNI with Network Policy support (Calico recommended)

### Deployment Steps

1. **Clone the repository and navigate to the k8s directory**:
   ```bash
   cd multi-agent-factory/infra/k8s
   ```

2. **Generate secrets** (first-time setup):
   ```bash
   ./generate-secrets.sh
   ```

3. **Deploy the infrastructure**:
   ```bash
   ./deploy.sh
   ```

4. **Verify the deployment**:
   ```bash
   ./deploy.sh verify
   ```

5. **Check deployment status**:
   ```bash
   ./deploy.sh status
   ```

## 🔧 Configuration

### Environment Variables

The following environment variables can be set before deployment:

```bash
# Deployment options
export DRY_RUN=true                    # Enable dry-run mode
export SKIP_VALIDATION=true            # Skip YAML validation
export NAMESPACE=multi-agent-factory   # Custom namespace

# Storage configuration
export STORAGE_CLASS=fast-ssd          # Primary storage class
export BACKUP_STORAGE_CLASS=backup-storage # Backup storage class

# Resource limits
export API_REPLICAS=3                  # API server replicas
export AGENT_REPLICAS=2                # Default agent replicas
```

### Secrets Configuration

Before deployment, you need to configure the following secrets in `01-secrets.yaml`:

- **Database credentials**: PostgreSQL username, password, and database name
- **Redis password**: Authentication for Redis cache
- **JWT secrets**: For API authentication
- **Encryption keys**: For data encryption at rest
- **NATS token**: For message queue authentication
- **LLM API keys**: OpenAI, Anthropic, or other LLM provider keys
- **TLS certificates**: SSL certificates for HTTPS
- **Registry credentials**: Docker registry authentication

## 🔐 Security Features

### Pod Security Standards
- **Restricted security context**: Non-root users, read-only filesystems
- **Capability dropping**: Minimal Linux capabilities
- **Seccomp profiles**: Runtime security profiles

### Network Security
- **Network policies**: Micro-segmentation and traffic control
- **Ingress security**: Rate limiting, IP whitelisting, WAF
- **Service mesh ready**: Compatible with Istio/Linkerd

### Security Scanning
- **Automated vulnerability scanning**: Weekly Trivy scans
- **Admission controllers**: Policy enforcement at deployment time
- **Security monitoring**: Real-time security event monitoring

## 📊 Monitoring & Observability

### Metrics Collection
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards
- **Custom metrics**: Application-specific metrics

### Distributed Tracing
- **Jaeger**: End-to-end request tracing
- **OpenTelemetry**: Standardized observability

### Logging
- **Fluent Bit**: Log collection and forwarding
- **Elasticsearch**: Log storage and indexing
- **Kibana**: Log analysis and visualization

### Access URLs

After deployment, access the monitoring tools:

```bash
# Port forwarding (if ingress is not available)
kubectl port-forward -n multi-agent-factory svc/grafana 3000:3000
kubectl port-forward -n multi-agent-factory svc/kibana 5601:5601
kubectl port-forward -n multi-agent-factory svc/prometheus 9090:9090
kubectl port-forward -n multi-agent-factory svc/jaeger 16686:16686
```

## 🔄 Backup & Recovery

### Automated Backups
- **Database backups**: Daily PostgreSQL dumps
- **Volume snapshots**: Daily EBS snapshots
- **Configuration backups**: Kubernetes resource exports

### Backup Schedule
- **Volume snapshots**: Daily at 1:00 AM UTC
- **Database backups**: Daily at 2:00 AM UTC
- **Redis backups**: Daily at 3:00 AM UTC

### Recovery Procedures

1. **Database recovery**:
   ```bash
   # Modify the restore job template
   kubectl apply -f 12-backup-recovery.yaml
   
   # Set the backup file to restore from
   kubectl set env job/postgres-restore-template RESTORE_BACKUP_FILE=backup_file.sql.gz
   
   # Run the restore job
   kubectl create job --from=job/postgres-restore-template postgres-restore-$(date +%s)
   ```

2. **Volume recovery**:
   ```bash
   # Create PVC from snapshot
   kubectl apply -f - <<EOF
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: postgres-pvc-restored
     namespace: multi-agent-factory
   spec:
     accessModes: ["ReadWriteOnce"]
     storageClassName: fast-ssd
     resources:
       requests:
         storage: 50Gi
     dataSource:
       name: postgres-snapshot-YYYYMMDD-HHMMSS
       kind: VolumeSnapshot
       apiGroup: snapshot.storage.k8s.io
   EOF
   ```

## ⚡ Scaling & Performance

### Horizontal Pod Autoscaling (HPA)
- **API servers**: Scale based on CPU, memory, and request rate
- **Agent workers**: Scale based on queue length and CPU usage
- **Custom metrics**: Application-specific scaling triggers

### Vertical Pod Autoscaling (VPA)
- **Automatic resource optimization**: Right-sizing containers
- **Resource recommendations**: Cost optimization insights

### Cluster Autoscaling
- **Node auto-scaling**: Automatic node provisioning
- **Multi-AZ deployment**: High availability across zones

## 🛠️ Operational Procedures

### Health Checks

```bash
# Check overall cluster health
kubectl get nodes
kubectl get pods -n multi-agent-factory

# Check specific component health
kubectl exec -n multi-agent-factory deployment/maf-api -- curl -f http://localhost:8000/health
kubectl exec -n multi-agent-factory deployment/postgres -- pg_isready
```

### Log Analysis

```bash
# View application logs
kubectl logs -n multi-agent-factory deployment/maf-api -f

# View agent logs
kubectl logs -n multi-agent-factory deployment/document-writer-agent -f

# Search logs in Kibana
# Access Kibana UI and search for specific patterns
```

### Performance Monitoring

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n multi-agent-factory

# View metrics in Grafana
# Access Grafana UI for detailed performance dashboards
```

### Troubleshooting

#### Common Issues

1. **Pods stuck in Pending state**:
   ```bash
   kubectl describe pod <pod-name> -n multi-agent-factory
   # Check for resource constraints or node affinity issues
   ```

2. **Database connection issues**:
   ```bash
   kubectl exec -n multi-agent-factory deployment/postgres -- psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"
   ```

3. **Network connectivity issues**:
   ```bash
   kubectl exec -n multi-agent-factory deployment/maf-api -- nslookup postgres
   ```

4. **Storage issues**:
   ```bash
   kubectl get pvc -n multi-agent-factory
   kubectl describe pvc <pvc-name> -n multi-agent-factory
   ```

## 🔄 Updates & Maintenance

### Rolling Updates

```bash
# Update API image
kubectl set image deployment/maf-api maf-api=your-registry/maf-api:v2.0.0 -n multi-agent-factory

# Update agent image
kubectl set image deployment/document-writer-agent agent=your-registry/maf-agent:v2.0.0 -n multi-agent-factory
```

### Configuration Updates

```bash
# Update configuration
kubectl apply -f 06-api.yaml

# Restart deployment to pick up changes
kubectl rollout restart deployment/maf-api -n multi-agent-factory
```

### Security Updates

```bash
# Run security scan
kubectl create job --from=cronjob/security-scan security-scan-manual -n multi-agent-factory

# Check scan results
kubectl logs job/security-scan-manual -n multi-agent-factory
```

## 🧹 Cleanup

### Remove Deployment

```bash
# Remove all MAF resources
./deploy.sh cleanup

# Or manually delete namespace
kubectl delete namespace multi-agent-factory
```

### Cleanup Storage

```bash
# Delete persistent volumes (WARNING: This will delete all data)
kubectl delete pvc --all -n multi-agent-factory

# Delete volume snapshots
kubectl delete volumesnapshots --all -n multi-agent-factory
```

## 📚 Additional Resources

### Documentation
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [Fluent Bit Documentation](https://docs.fluentbit.io/)

### Best Practices
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Monitoring Best Practices](https://prometheus.io/docs/practices/)

### Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Kubernetes events: `kubectl get events -n multi-agent-factory`
3. Check application logs in Kibana
4. Monitor metrics in Grafana
5. Create an issue in the project repository

## 🏷️ Version Information

- **Kubernetes**: v1.25+
- **PostgreSQL**: 15
- **Redis**: 7
- **NATS**: 2.10
- **Prometheus**: Latest
- **Grafana**: Latest
- **Elasticsearch**: 8.11
- **Fluent Bit**: 2.2

---

**Note**: This infrastructure is designed for production use. Ensure you have proper backup procedures, monitoring, and security measures in place before deploying to production environments.