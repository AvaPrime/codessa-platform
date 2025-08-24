#!/bin/bash

# Multi-Agent Factory Secrets Generation Script
# This script generates secure secrets for the MAF Kubernetes deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="multi-agent-factory"
SECRETS_FILE="01-secrets.yaml"
ENV_FILE=".env.secrets"

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

# Function to generate random password
generate_password() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate JWT secret
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "\n"
}

# Function to generate encryption key
generate_encryption_key() {
    openssl rand -hex 32
}

# Function to generate NATS token
generate_nats_token() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Function to encode base64
base64_encode() {
    echo -n "$1" | base64 -w 0
}

# Function to prompt for input with default
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local secret="$3"
    
    if [ "$secret" = "true" ]; then
        echo -n "$prompt [$default]: "
        read -s input
        echo
    else
        echo -n "$prompt [$default]: "
        read input
    fi
    
    echo "${input:-$default}"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if openssl is installed
    if ! command -v openssl &> /dev/null; then
        print_error "openssl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if base64 is installed
    if ! command -v base64 &> /dev/null; then
        print_error "base64 is not installed or not in PATH"
        exit 1
    fi
    
    print_success "Prerequisites check completed"
}

# Function to collect user inputs
collect_inputs() {
    print_status "Collecting configuration inputs..."
    echo ""
    echo "Please provide the following information for your MAF deployment:"
    echo "(Press Enter to use default values)"
    echo ""
    
    # Database configuration
    echo "📊 Database Configuration:"
    POSTGRES_USER=$(prompt_with_default "PostgreSQL username" "maf_user")
    POSTGRES_PASSWORD=$(prompt_with_default "PostgreSQL password" "$(generate_password 24)" "true")
    POSTGRES_DB=$(prompt_with_default "PostgreSQL database name" "maf_db")
    echo ""
    
    # Redis configuration
    echo "🔴 Redis Configuration:"
    REDIS_PASSWORD=$(prompt_with_default "Redis password" "$(generate_password 24)" "true")
    echo ""
    
    # Security configuration
    echo "🔐 Security Configuration:"
    JWT_SECRET=$(prompt_with_default "JWT secret key" "$(generate_jwt_secret)" "true")
    ENCRYPTION_KEY=$(prompt_with_default "Encryption key" "$(generate_encryption_key)" "true")
    echo ""
    
    # NATS configuration
    echo "📨 NATS Configuration:"
    NATS_TOKEN=$(prompt_with_default "NATS authentication token" "$(generate_nats_token)" "true")
    echo ""
    
    # LLM API Keys
    echo "🤖 LLM API Configuration:"
    OPENAI_API_KEY=$(prompt_with_default "OpenAI API key" "" "true")
    ANTHROPIC_API_KEY=$(prompt_with_default "Anthropic API key (optional)" "" "true")
    GOOGLE_API_KEY=$(prompt_with_default "Google AI API key (optional)" "" "true")
    echo ""
    
    # AWS Configuration (for backups)
    echo "☁️ AWS Configuration (for backups - optional):"
    AWS_ACCESS_KEY_ID=$(prompt_with_default "AWS Access Key ID" "")
    AWS_SECRET_ACCESS_KEY=$(prompt_with_default "AWS Secret Access Key" "" "true")
    AWS_S3_BUCKET=$(prompt_with_default "AWS S3 Bucket for backups" "")
    echo ""
    
    # Docker Registry
    echo "🐳 Docker Registry Configuration:"
    DOCKER_REGISTRY=$(prompt_with_default "Docker registry URL" "your-registry.com")
    DOCKER_USERNAME=$(prompt_with_default "Docker registry username" "")
    DOCKER_PASSWORD=$(prompt_with_default "Docker registry password" "" "true")
    echo ""
    
    # TLS Configuration
    echo "🔒 TLS Configuration:"
    echo "Do you want to generate self-signed certificates? (y/N)"
    read -r generate_certs
    
    if [[ "$generate_certs" =~ ^[Yy]$ ]]; then
        DOMAIN=$(prompt_with_default "Domain name for certificates" "maf.local")
        generate_self_signed_certs
    else
        echo "Please provide your TLS certificate and key:"
        echo "Certificate file path (leave empty to skip):"
        read TLS_CERT_FILE
        echo "Private key file path (leave empty to skip):"
        read TLS_KEY_FILE
        
        if [ -n "$TLS_CERT_FILE" ] && [ -f "$TLS_CERT_FILE" ]; then
            TLS_CERT=$(cat "$TLS_CERT_FILE")
        else
            TLS_CERT=""
        fi
        
        if [ -n "$TLS_KEY_FILE" ] && [ -f "$TLS_KEY_FILE" ]; then
            TLS_KEY=$(cat "$TLS_KEY_FILE")
        else
            TLS_KEY=""
        fi
    fi
    
    print_success "Configuration inputs collected"
}

# Function to generate self-signed certificates
generate_self_signed_certs() {
    print_status "Generating self-signed TLS certificates..."
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    
    # Generate private key
    openssl genrsa -out "$TEMP_DIR/tls.key" 2048
    
    # Generate certificate
    openssl req -new -x509 -key "$TEMP_DIR/tls.key" -out "$TEMP_DIR/tls.crt" -days 365 -subj "/CN=$DOMAIN/O=MAF/C=US"
    
    # Read certificate and key
    TLS_CERT=$(cat "$TEMP_DIR/tls.crt")
    TLS_KEY=$(cat "$TEMP_DIR/tls.key")
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    print_success "Self-signed certificates generated for domain: $DOMAIN"
}

# Function to create Docker registry secret
create_docker_secret() {
    if [ -n "$DOCKER_USERNAME" ] && [ -n "$DOCKER_PASSWORD" ]; then
        local auth=$(echo -n "$DOCKER_USERNAME:$DOCKER_PASSWORD" | base64 -w 0)
        local config='{"auths":{"'$DOCKER_REGISTRY'":{"username":"'$DOCKER_USERNAME'","password":"'$DOCKER_PASSWORD'","auth":"'$auth'"}}}'
        echo -n "$config" | base64 -w 0
    else
        echo ""
    fi
}

# Function to generate secrets YAML
generate_secrets_yaml() {
    print_status "Generating secrets YAML file..."
    
    cat > "$SECRETS_FILE" << EOF
# Multi-Agent Factory Kubernetes Secrets
# Generated on $(date)
# WARNING: This file contains sensitive information. Keep it secure!

apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
  labels:
    name: $NAMESPACE
    app.kubernetes.io/name: multi-agent-factory
    app.kubernetes.io/component: namespace

---
# Main application secrets
apiVersion: v1
kind: Secret
metadata:
  name: maf-secrets
  namespace: $NAMESPACE
  labels:
    app.kubernetes.io/name: maf-secrets
    app.kubernetes.io/component: secrets
type: Opaque
data:
  # Database configuration
  POSTGRES_USER: $(base64_encode "$POSTGRES_USER")
  POSTGRES_PASSWORD: $(base64_encode "$POSTGRES_PASSWORD")
  POSTGRES_DB: $(base64_encode "$POSTGRES_DB")
  DATABASE_URL: $(base64_encode "postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB")
  
  # Redis configuration
  REDIS_PASSWORD: $(base64_encode "$REDIS_PASSWORD")
  REDIS_URL: $(base64_encode "redis://:$REDIS_PASSWORD@redis:6379/0")
  
  # Security configuration
  JWT_SECRET: $(base64_encode "$JWT_SECRET")
  ENCRYPTION_KEY: $(base64_encode "$ENCRYPTION_KEY")
  
  # NATS configuration
  NATS_TOKEN: $(base64_encode "$NATS_TOKEN")
  NATS_URL: $(base64_encode "nats://token:$NATS_TOKEN@nats:4222")
  
  # LLM API Keys
  OPENAI_API_KEY: $(base64_encode "$OPENAI_API_KEY")
EOF

    # Add optional API keys if provided
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "  ANTHROPIC_API_KEY: $(base64_encode "$ANTHROPIC_API_KEY")" >> "$SECRETS_FILE"
    fi
    
    if [ -n "$GOOGLE_API_KEY" ]; then
        echo "  GOOGLE_API_KEY: $(base64_encode "$GOOGLE_API_KEY")" >> "$SECRETS_FILE"
    fi
    
    # Add AWS configuration if provided
    if [ -n "$AWS_ACCESS_KEY_ID" ]; then
        cat >> "$SECRETS_FILE" << EOF
  
  # AWS configuration (for backups)
  AWS_ACCESS_KEY_ID: $(base64_encode "$AWS_ACCESS_KEY_ID")
EOF
    fi
    
    if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
        echo "  AWS_SECRET_ACCESS_KEY: $(base64_encode "$AWS_SECRET_ACCESS_KEY")" >> "$SECRETS_FILE"
    fi
    
    if [ -n "$AWS_S3_BUCKET" ]; then
        echo "  AWS_S3_BUCKET: $(base64_encode "$AWS_S3_BUCKET")" >> "$SECRETS_FILE"
    fi
    
    # Add TLS secret if certificates are provided
    if [ -n "$TLS_CERT" ] && [ -n "$TLS_KEY" ]; then
        cat >> "$SECRETS_FILE" << EOF

---
# TLS certificates
apiVersion: v1
kind: Secret
metadata:
  name: maf-tls-secret
  namespace: $NAMESPACE
  labels:
    app.kubernetes.io/name: maf-tls-secret
    app.kubernetes.io/component: secrets
type: kubernetes.io/tls
data:
  tls.crt: $(base64_encode "$TLS_CERT")
  tls.key: $(base64_encode "$TLS_KEY")
EOF
    fi
    
    # Add Docker registry secret if provided
    local docker_config=$(create_docker_secret)
    if [ -n "$docker_config" ]; then
        cat >> "$SECRETS_FILE" << EOF

---
# Docker registry credentials
apiVersion: v1
kind: Secret
metadata:
  name: maf-registry-secret
  namespace: $NAMESPACE
  labels:
    app.kubernetes.io/name: maf-registry-secret
    app.kubernetes.io/component: secrets
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: $docker_config
EOF
    fi
    
    print_success "Secrets YAML file generated: $SECRETS_FILE"
}

# Function to generate environment file
generate_env_file() {
    print_status "Generating environment file for reference..."
    
    cat > "$ENV_FILE" << EOF
# Multi-Agent Factory Environment Variables
# Generated on $(date)
# This file is for reference only - actual secrets are in Kubernetes

# Database configuration
POSTGRES_USER=$POSTGRES_USER
POSTGRES_DB=$POSTGRES_DB
DATABASE_URL=postgresql://$POSTGRES_USER:****@postgres:5432/$POSTGRES_DB

# Redis configuration
REDIS_URL=redis://:****@redis:6379/0

# NATS configuration
NATS_URL=nats://token:****@nats:4222

# LLM API Keys (masked)
OPENAI_API_KEY=${OPENAI_API_KEY:0:8}****
EOF

    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:0:8}****" >> "$ENV_FILE"
    fi
    
    if [ -n "$GOOGLE_API_KEY" ]; then
        echo "GOOGLE_API_KEY=${GOOGLE_API_KEY:0:8}****" >> "$ENV_FILE"
    fi
    
    if [ -n "$AWS_ACCESS_KEY_ID" ]; then
        cat >> "$ENV_FILE" << EOF

# AWS configuration
AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
AWS_S3_BUCKET=$AWS_S3_BUCKET
EOF
    fi
    
    if [ -n "$DOCKER_REGISTRY" ]; then
        cat >> "$ENV_FILE" << EOF

# Docker registry
DOCKER_REGISTRY=$DOCKER_REGISTRY
DOCKER_USERNAME=$DOCKER_USERNAME
EOF
    fi
    
    print_success "Environment file generated: $ENV_FILE"
}

# Function to validate secrets
validate_secrets() {
    print_status "Validating generated secrets..."
    
    # Check if secrets file exists and is valid YAML
    if [ ! -f "$SECRETS_FILE" ]; then
        print_error "Secrets file not found: $SECRETS_FILE"
        return 1
    fi
    
    # Validate YAML syntax
    if command -v kubectl &> /dev/null; then
        if kubectl apply --dry-run=client -f "$SECRETS_FILE" &> /dev/null; then
            print_success "✓ Secrets YAML is valid"
        else
            print_error "✗ Secrets YAML has validation errors"
            return 1
        fi
    else
        print_warning "kubectl not found, skipping YAML validation"
    fi
    
    # Check required secrets
    local required_secrets=("POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB" "REDIS_PASSWORD" "JWT_SECRET" "ENCRYPTION_KEY" "NATS_TOKEN" "OPENAI_API_KEY")
    
    for secret in "${required_secrets[@]}"; do
        if grep -q "$secret:" "$SECRETS_FILE"; then
            print_success "✓ $secret is present"
        else
            print_error "✗ $secret is missing"
            return 1
        fi
    done
    
    print_success "Secrets validation completed"
}

# Function to show security recommendations
show_security_recommendations() {
    print_status "Security Recommendations:"
    echo ""
    echo "🔐 Security Best Practices:"
    echo "  1. Store the secrets file ($SECRETS_FILE) securely"
    echo "  2. Do not commit secrets to version control"
    echo "  3. Use a secrets management system in production"
    echo "  4. Rotate secrets regularly"
    echo "  5. Use strong, unique passwords for each service"
    echo "  6. Enable encryption at rest for your cluster"
    echo "  7. Use network policies to restrict traffic"
    echo "  8. Monitor for unauthorized access"
    echo ""
    echo "📁 File Security:"
    echo "  - Add $SECRETS_FILE to .gitignore"
    echo "  - Set restrictive file permissions: chmod 600 $SECRETS_FILE"
    echo "  - Consider using sealed-secrets or external-secrets operator"
    echo ""
    echo "🔄 Next Steps:"
    echo "  1. Review the generated secrets file"
    echo "  2. Deploy using: ./deploy.sh"
    echo "  3. Verify deployment: ./deploy.sh verify"
    echo ""
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --interactive    Interactive mode (default)"
    echo "  --from-env       Generate from environment variables"
    echo "  --validate-only  Only validate existing secrets file"
    echo "  --help           Show this help message"
    echo ""
    echo "Environment Variables (for --from-env mode):"
    echo "  POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB"
    echo "  REDIS_PASSWORD"
    echo "  JWT_SECRET, ENCRYPTION_KEY"
    echo "  NATS_TOKEN"
    echo "  OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY"
    echo "  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET"
    echo "  DOCKER_REGISTRY, DOCKER_USERNAME, DOCKER_PASSWORD"
    echo "  TLS_CERT_FILE, TLS_KEY_FILE"
    echo ""
}

# Function to generate from environment variables
generate_from_env() {
    print_status "Generating secrets from environment variables..."
    
    # Set defaults for missing variables
    POSTGRES_USER=${POSTGRES_USER:-"maf_user"}
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-$(generate_password 24)}
    POSTGRES_DB=${POSTGRES_DB:-"maf_db"}
    REDIS_PASSWORD=${REDIS_PASSWORD:-$(generate_password 24)}
    JWT_SECRET=${JWT_SECRET:-$(generate_jwt_secret)}
    ENCRYPTION_KEY=${ENCRYPTION_KEY:-$(generate_encryption_key)}
    NATS_TOKEN=${NATS_TOKEN:-$(generate_nats_token)}
    DOCKER_REGISTRY=${DOCKER_REGISTRY:-"your-registry.com"}
    
    # Load TLS certificates if files are specified
    if [ -n "$TLS_CERT_FILE" ] && [ -f "$TLS_CERT_FILE" ]; then
        TLS_CERT=$(cat "$TLS_CERT_FILE")
    fi
    
    if [ -n "$TLS_KEY_FILE" ] && [ -f "$TLS_KEY_FILE" ]; then
        TLS_KEY=$(cat "$TLS_KEY_FILE")
    fi
    
    print_success "Secrets loaded from environment variables"
}

# Main function
main() {
    local mode="interactive"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interactive)
                mode="interactive"
                shift
                ;;
            --from-env)
                mode="from-env"
                shift
                ;;
            --validate-only)
                mode="validate-only"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    print_status "Multi-Agent Factory Secrets Generator"
    echo ""
    
    check_prerequisites
    
    case "$mode" in
        "interactive")
            collect_inputs
            generate_secrets_yaml
            generate_env_file
            validate_secrets
            ;;
        "from-env")
            generate_from_env
            generate_secrets_yaml
            generate_env_file
            validate_secrets
            ;;
        "validate-only")
            validate_secrets
            exit $?
            ;;
    esac
    
    # Set secure file permissions
    chmod 600 "$SECRETS_FILE" 2>/dev/null || true
    chmod 600 "$ENV_FILE" 2>/dev/null || true
    
    show_security_recommendations
    
    print_success "🎉 Secrets generation completed successfully!"
    print_status "Generated files:"
    echo "  - $SECRETS_FILE (Kubernetes secrets)"
    echo "  - $ENV_FILE (Environment reference)"
}

# Run main function
main "$@"