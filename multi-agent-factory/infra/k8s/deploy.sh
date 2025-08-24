#!/bin/bash

# Multi-Agent Factory Kubernetes Deployment Script
# This script deploys the complete MAF infrastructure to Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="multi-agent-factory"
KUBECTL_TIMEOUT="300s"
DRY_RUN=${DRY_RUN:-false}
SKIP_VALIDATION=${SKIP_VALIDATION:-false}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        print_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if running as cluster admin
    if ! kubectl auth can-i '*' '*' --all-namespaces &> /dev/null; then
        print_warning "You may not have cluster admin privileges. Some operations might fail."
    fi
    
    print_success "Prerequisites check completed"
}

# Function to validate YAML files
validate_yaml_files() {
    if [ "$SKIP_VALIDATION" = "true" ]; then
        print_warning "Skipping YAML validation"
        return
    fi
    
    print_status "Validating YAML files..."
    
    local files=("01-secrets.yaml" "02-storage.yaml" "03-database.yaml" "04-redis.yaml" 
                 "05-nats.yaml" "06-api.yaml" "07-agents.yaml" "08-ingress.yaml" 
                 "09-monitoring.yaml" "10-autoscaling.yaml" "11-network-policies.yaml" 
                 "12-backup-recovery.yaml" "13-security.yaml" "14-logging-observability.yaml")
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            if kubectl apply --dry-run=client -f "$file" &> /dev/null; then
                print_success "✓ $file is valid"
            else
                print_error "✗ $file has validation errors"
                kubectl apply --dry-run=client -f "$file"
                exit 1
            fi
        else
            print_warning "File $file not found, skipping validation"
        fi
    done
    
    print_success "YAML validation completed"
}

# Function to create namespace
create_namespace() {
    print_status "Creating namespace: $NAMESPACE"
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_warning "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace "$NAMESPACE"
        print_success "Namespace $NAMESPACE created"
    fi
    
    # Label namespace for monitoring
    kubectl label namespace "$NAMESPACE" monitoring=enabled --overwrite
    kubectl label namespace "$NAMESPACE" name="$NAMESPACE" --overwrite
}

# Function to deploy secrets
deploy_secrets() {
    print_status "Deploying secrets..."
    
    if [ ! -f "01-secrets.yaml" ]; then
        print_error "01-secrets.yaml not found. Please create secrets first."
        print_error "Run: ./generate-secrets.sh"
        exit 1
    fi
    
    kubectl apply -f 01-secrets.yaml
    print_success "Secrets deployed"
}

# Function to deploy storage
deploy_storage() {
    print_status "Deploying storage components..."
    kubectl apply -f 02-storage.yaml
    
    # Wait for storage classes to be ready
    print_status "Waiting for storage classes to be ready..."
    kubectl wait --for=condition=Ready storageclass/fast-ssd --timeout=$KUBECTL_TIMEOUT || true
    kubectl wait --for=condition=Ready storageclass/backup-storage --timeout=$KUBECTL_TIMEOUT || true
    
    print_success "Storage components deployed"
}

# Function to deploy database
deploy_database() {
    print_status "Deploying PostgreSQL database..."
    kubectl apply -f 03-database.yaml
    
    # Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=postgres -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    
    print_success "PostgreSQL database deployed"
}

# Function to deploy Redis
deploy_redis() {
    print_status "Deploying Redis..."
    kubectl apply -f 04-redis.yaml
    
    # Wait for Redis to be ready
    print_status "Waiting for Redis to be ready..."
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=redis -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    
    print_success "Redis deployed"
}

# Function to deploy NATS
deploy_nats() {
    print_status "Deploying NATS messaging..."
    kubectl apply -f 05-nats.yaml
    
    # Wait for NATS to be ready
    print_status "Waiting for NATS to be ready..."
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=nats -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    
    print_success "NATS messaging deployed"
}

# Function to deploy API
deploy_api() {
    print_status "Deploying MAF API..."
    kubectl apply -f 06-api.yaml
    
    # Wait for API to be ready
    print_status "Waiting for API to be ready..."
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=maf-api -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    
    print_success "MAF API deployed"
}

# Function to deploy agents
deploy_agents() {
    print_status "Deploying MAF agents..."
    kubectl apply -f 07-agents.yaml
    
    # Wait for agents to be ready
    print_status "Waiting for agents to be ready..."
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=agent -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    
    print_success "MAF agents deployed"
}

# Function to deploy ingress
deploy_ingress() {
    print_status "Deploying ingress configuration..."
    
    # Check if ingress controller is installed
    if ! kubectl get ingressclass nginx &> /dev/null; then
        print_warning "NGINX Ingress Controller not found. Installing..."
        helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
        helm repo update
        helm install ingress-nginx ingress-nginx/ingress-nginx \
            --namespace ingress-nginx \
            --create-namespace \
            --set controller.metrics.enabled=true \
            --set controller.podAnnotations."prometheus\.io/scrape"="true" \
            --set controller.podAnnotations."prometheus\.io/port"="10254"
        
        # Wait for ingress controller to be ready
        kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx --timeout=$KUBECTL_TIMEOUT
    fi
    
    kubectl apply -f 08-ingress.yaml
    print_success "Ingress configuration deployed"
}

# Function to deploy monitoring
deploy_monitoring() {
    print_status "Deploying monitoring stack..."
    kubectl apply -f 09-monitoring.yaml
    
    # Wait for monitoring components to be ready
    print_status "Waiting for monitoring components to be ready..."
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=prometheus -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=grafana -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    
    print_success "Monitoring stack deployed"
}

# Function to deploy autoscaling
deploy_autoscaling() {
    print_status "Deploying autoscaling configuration..."
    
    # Check if metrics server is installed
    if ! kubectl get deployment metrics-server -n kube-system &> /dev/null; then
        print_warning "Metrics server not found. Installing..."
        kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
        kubectl wait --for=condition=Ready pod -l k8s-app=metrics-server -n kube-system --timeout=$KUBECTL_TIMEOUT
    fi
    
    kubectl apply -f 10-autoscaling.yaml
    print_success "Autoscaling configuration deployed"
}

# Function to deploy network policies
deploy_network_policies() {
    print_status "Deploying network policies..."
    kubectl apply -f 11-network-policies.yaml
    print_success "Network policies deployed"
}

# Function to deploy backup and recovery
deploy_backup_recovery() {
    print_status "Deploying backup and recovery..."
    kubectl apply -f 12-backup-recovery.yaml
    print_success "Backup and recovery deployed"
}

# Function to deploy security
deploy_security() {
    print_status "Deploying security configuration..."
    kubectl apply -f 13-security.yaml
    print_success "Security configuration deployed"
}

# Function to deploy logging and observability
deploy_logging_observability() {
    print_status "Deploying logging and observability..."
    kubectl apply -f 14-logging-observability.yaml
    
    # Wait for logging components to be ready
    print_status "Waiting for logging components to be ready..."
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=elasticsearch -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=kibana -n "$NAMESPACE" --timeout=$KUBECTL_TIMEOUT
    
    print_success "Logging and observability deployed"
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check all pods are running
    print_status "Checking pod status..."
    kubectl get pods -n "$NAMESPACE" -o wide
    
    # Check services
    print_status "Checking services..."
    kubectl get services -n "$NAMESPACE"
    
    # Check ingress
    print_status "Checking ingress..."
    kubectl get ingress -n "$NAMESPACE"
    
    # Check persistent volumes
    print_status "Checking persistent volumes..."
    kubectl get pvc -n "$NAMESPACE"
    
    # Health check
    print_status "Performing health checks..."
    
    # Check if API is responding
    API_POD=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=maf-api -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$API_POD" ]; then
        if kubectl exec -n "$NAMESPACE" "$API_POD" -- curl -f http://localhost:8000/health &> /dev/null; then
            print_success "✓ API health check passed"
        else
            print_warning "✗ API health check failed"
        fi
    fi
    
    # Check database connectivity
    DB_POD=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=postgres -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$DB_POD" ]; then
        if kubectl exec -n "$NAMESPACE" "$DB_POD" -- pg_isready &> /dev/null; then
            print_success "✓ Database connectivity check passed"
        else
            print_warning "✗ Database connectivity check failed"
        fi
    fi
    
    print_success "Deployment verification completed"
}

# Function to show access information
show_access_info() {
    print_status "Access Information:"
    
    # Get ingress IP
    INGRESS_IP=$(kubectl get ingress maf-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "<pending>")
    if [ "$INGRESS_IP" = "<pending>" ]; then
        INGRESS_IP=$(kubectl get ingress maf-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "<pending>")
    fi
    
    echo ""
    echo "🌐 MAF API: https://$INGRESS_IP/api/v1"
    echo "📊 Grafana: http://$INGRESS_IP:3000 (admin/admin)"
    echo "🔍 Kibana: http://$INGRESS_IP:5601"
    echo "📈 Prometheus: http://$INGRESS_IP:9090"
    echo "🔍 Jaeger: http://$INGRESS_IP:16686"
    echo ""
    
    # Port forwarding commands
    echo "Port forwarding commands (if ingress is not available):"
    echo "kubectl port-forward -n $NAMESPACE svc/maf-api 8000:8000"
    echo "kubectl port-forward -n $NAMESPACE svc/grafana 3000:3000"
    echo "kubectl port-forward -n $NAMESPACE svc/kibana 5601:5601"
    echo "kubectl port-forward -n $NAMESPACE svc/prometheus 9090:9090"
    echo "kubectl port-forward -n $NAMESPACE svc/jaeger 16686:16686"
    echo ""
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy     Deploy the complete MAF infrastructure (default)"
    echo "  verify     Verify the deployment"
    echo "  cleanup    Remove all MAF resources"
    echo "  status     Show deployment status"
    echo ""
    echo "Options:"
    echo "  --dry-run           Show what would be deployed without actually deploying"
    echo "  --skip-validation   Skip YAML validation"
    echo "  --namespace NAME    Use custom namespace (default: multi-agent-factory)"
    echo "  --help              Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DRY_RUN=true        Enable dry-run mode"
    echo "  SKIP_VALIDATION=true Skip YAML validation"
    echo ""
}

# Function to cleanup deployment
cleanup_deployment() {
    print_warning "This will delete all MAF resources. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Cleaning up MAF deployment..."
        
        # Delete in reverse order
        kubectl delete -f 14-logging-observability.yaml --ignore-not-found=true
        kubectl delete -f 13-security.yaml --ignore-not-found=true
        kubectl delete -f 12-backup-recovery.yaml --ignore-not-found=true
        kubectl delete -f 11-network-policies.yaml --ignore-not-found=true
        kubectl delete -f 10-autoscaling.yaml --ignore-not-found=true
        kubectl delete -f 09-monitoring.yaml --ignore-not-found=true
        kubectl delete -f 08-ingress.yaml --ignore-not-found=true
        kubectl delete -f 07-agents.yaml --ignore-not-found=true
        kubectl delete -f 06-api.yaml --ignore-not-found=true
        kubectl delete -f 05-nats.yaml --ignore-not-found=true
        kubectl delete -f 04-redis.yaml --ignore-not-found=true
        kubectl delete -f 03-database.yaml --ignore-not-found=true
        kubectl delete -f 02-storage.yaml --ignore-not-found=true
        kubectl delete -f 01-secrets.yaml --ignore-not-found=true
        
        # Delete namespace
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
        
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Function to show deployment status
show_status() {
    print_status "MAF Deployment Status:"
    echo ""
    
    # Namespace status
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_success "✓ Namespace: $NAMESPACE exists"
    else
        print_error "✗ Namespace: $NAMESPACE not found"
        return 1
    fi
    
    # Pod status
    echo ""
    print_status "Pod Status:"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    # Service status
    echo ""
    print_status "Service Status:"
    kubectl get services -n "$NAMESPACE"
    
    # PVC status
    echo ""
    print_status "Storage Status:"
    kubectl get pvc -n "$NAMESPACE"
    
    # Ingress status
    echo ""
    print_status "Ingress Status:"
    kubectl get ingress -n "$NAMESPACE"
}

# Main deployment function
main_deploy() {
    print_status "Starting MAF Kubernetes deployment..."
    
    if [ "$DRY_RUN" = "true" ]; then
        print_warning "DRY RUN MODE - No actual changes will be made"
        return
    fi
    
    check_prerequisites
    validate_yaml_files
    create_namespace
    deploy_secrets
    deploy_storage
    deploy_database
    deploy_redis
    deploy_nats
    deploy_api
    deploy_agents
    deploy_ingress
    deploy_monitoring
    deploy_autoscaling
    deploy_network_policies
    deploy_backup_recovery
    deploy_security
    deploy_logging_observability
    
    print_success "🎉 MAF deployment completed successfully!"
    
    verify_deployment
    show_access_info
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        deploy)
            COMMAND="deploy"
            shift
            ;;
        verify)
            COMMAND="verify"
            shift
            ;;
        cleanup)
            COMMAND="cleanup"
            shift
            ;;
        status)
            COMMAND="status"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Execute command
case "${COMMAND:-deploy}" in
    deploy)
        main_deploy
        ;;
    verify)
        verify_deployment
        ;;
    cleanup)
        cleanup_deployment
        ;;
    status)
        show_status
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac