# CI/CD Pipeline Setup Guide

## Overview

This guide provides comprehensive instructions for setting up CI/CD pipelines for all Codessa Platform services using the provided workflow templates. Each template is designed to handle specific technology stacks and deployment patterns.

## Available Templates

### 1. Node.js Service Template
**File**: `.github/workflow-templates/nodejs-service-ci-cd.yml`
**Use Cases**: Backend services, APIs, microservices
**Services**: codessa-core, codessa-llm-router, devgenie, echoforge, gitguard, docfoundry

### 2. Python Service Template
**File**: `.github/workflow-templates/python-service-ci-cd.yml`
**Use Cases**: ML services, data processing, AI services
**Services**: codessa-memory, codessa-metamind, aetherion-soulforge

### 3. Frontend React Template
**File**: `.github/workflow-templates/frontend-react-ci-cd.yml`
**Use Cases**: Web applications, dashboards, user interfaces
**Services**: echopilot, pondskipperhq

## Quick Setup

### Step 1: Choose the Right Template

```bash
# For Node.js services
cp .github/workflow-templates/nodejs-service-ci-cd.yml .github/workflows/ci-cd.yml

# For Python services
cp .github/workflow-templates/python-service-ci-cd.yml .github/workflows/ci-cd.yml

# For React frontends
cp .github/workflow-templates/frontend-react-ci-cd.yml .github/workflows/ci-cd.yml
```

### Step 2: Configure Repository Secrets

Add the following secrets to your GitHub repository:

#### Required Secrets (All Services)
```yaml
GITHUB_TOKEN: # Automatically provided by GitHub
SLACK_WEBHOOK: # Slack webhook URL for notifications
SONAR_TOKEN: # SonarCloud token for code analysis
SNYK_TOKEN: # Snyk token for security scanning
```

#### Kubernetes Deployment Secrets
```yaml
KUBE_CONFIG_STAGING: # Base64 encoded kubeconfig for staging
KUBE_CONFIG_PRODUCTION: # Base64 encoded kubeconfig for production
```

#### Frontend-Specific Secrets
```yaml
NETLIFY_AUTH_TOKEN: # Netlify deployment token (optional)
NETLIFY_SITE_ID: # Netlify site ID (optional)
CHROMATIC_PROJECT_TOKEN: # Chromatic visual testing token
LHCI_GITHUB_APP_TOKEN: # Lighthouse CI token
WPT_API_KEY: # WebPageTest API key
```

### Step 3: Update Package.json Scripts

Ensure your `package.json` includes the required scripts:

#### Node.js Services
```json
{
  "scripts": {
    "start": "node dist/index.js",
    "dev": "nodemon src/index.ts",
    "build": "tsc",
    "test": "jest",
    "test:unit": "jest --testPathPattern=unit",
    "test:integration": "jest --testPathPattern=integration",
    "test:smoke": "jest --testPathPattern=smoke",
    "test:production": "jest --testPathPattern=production",
    "test:load": "artillery run load-tests.yml",
    "lint": "eslint src/**/*.ts",
    "lint:fix": "eslint src/**/*.ts --fix",
    "format:check": "prettier --check src/**/*.ts",
    "format:fix": "prettier --write src/**/*.ts",
    "type-check": "tsc --noEmit"
  }
}
```

#### Python Services
```json
{
  "scripts": {
    "test:smoke": "pytest tests/smoke/",
    "test:production": "pytest tests/production/"
  }
}
```

And in your Python project, ensure these commands work:
```bash
# Code quality
black --check .
isort --check-only .
flake8 .
mypy .
bandit -r .

# Testing
pytest tests/unit/ --cov=src
pytest tests/integration/

# Security
safety check
```

#### React Frontends
```json
{
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "test:unit": "react-scripts test --testPathPattern=unit --watchAll=false",
    "test:components": "react-scripts test --testPathPattern=components --watchAll=false",
    "test:e2e": "playwright test",
    "test:a11y": "jest-axe",
    "test:smoke": "cypress run --env configFile=staging",
    "test:production": "cypress run --env configFile=production",
    "lint": "eslint src/**/*.{js,jsx,ts,tsx}",
    "lint:fix": "eslint src/**/*.{js,jsx,ts,tsx} --fix",
    "format:check": "prettier --check src/**/*.{js,jsx,ts,tsx}",
    "format:fix": "prettier --write src/**/*.{js,jsx,ts,tsx}",
    "type-check": "tsc --noEmit",
    "build-storybook": "build-storybook"
  }
}
```

## Service-Specific Configuration

### Codessa Core (Node.js)

```yaml
# .github/workflows/ci-cd.yml
name: Codessa Core CI/CD

env:
  NODE_VERSION: '18.x'
  SERVICE_NAME: 'codessa-core'
  HEALTH_CHECK_PATH: '/api/health'
  
# Add service-specific environment variables
jobs:
  quality:
    steps:
    - name: Database migration test
      run: npm run db:migrate:test
      env:
        DATABASE_URL: postgresql://test:test@localhost:5432/codessa_test
```

### Codessa Memory (Python)

```yaml
# .github/workflows/ci-cd.yml
name: Codessa Memory CI/CD

env:
  PYTHON_VERSION: '3.11'
  SERVICE_NAME: 'codessa-memory'
  
jobs:
  quality:
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    
    steps:
    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y libpq-dev
```

### EchoPilot (React)

```yaml
# .github/workflows/ci-cd.yml
name: EchoPilot CI/CD

env:
  NODE_VERSION: '18.x'
  SERVICE_NAME: 'echopilot'
  
jobs:
  build:
    steps:
    - name: Build application
      run: npm run build
      env:
        REACT_APP_API_URL: https://api.codessa.dev
        REACT_APP_WS_URL: wss://ws.codessa.dev
        REACT_APP_VERSION: ${{ github.sha }}
```

## Docker Configuration

### Node.js Dockerfile Template

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine AS production

WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Copy built application
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app/package*.json ./

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

USER nodejs

EXPOSE 3000

CMD ["npm", "start"]
```

### Python Dockerfile Template

```dockerfile
# Dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --disabled-password --gecos '' --uid 1001 appuser

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### React Dockerfile Template

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine AS production

# Copy built app
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80 || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

## Kubernetes Deployment

### Service Deployment Template

```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: SERVICE_NAME
  namespace: NAMESPACE
  labels:
    app: SERVICE_NAME
    version: VERSION
spec:
  replicas: 3
  selector:
    matchLabels:
      app: SERVICE_NAME
  template:
    metadata:
      labels:
        app: SERVICE_NAME
        version: VERSION
    spec:
      containers:
      - name: SERVICE_NAME
        image: ghcr.io/codessa-platform/SERVICE_NAME:VERSION
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: PORT
          value: "3000"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: SERVICE_NAME
  namespace: NAMESPACE
spec:
  selector:
    app: SERVICE_NAME
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: ClusterIP
```

## Environment Configuration

### Staging Environment

```yaml
# k8s/staging/kustomization.yml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- ../base

namespace: staging

replicas:
- name: SERVICE_NAME
  count: 2

images:
- name: ghcr.io/codessa-platform/SERVICE_NAME
  newTag: staging-latest

configMapGenerator:
- name: app-config
  literals:
  - NODE_ENV=staging
  - LOG_LEVEL=debug
  - API_URL=https://staging-api.codessa.dev
```

### Production Environment

```yaml
# k8s/production/kustomization.yml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- ../base

namespace: production

replicas:
- name: SERVICE_NAME
  count: 5

images:
- name: ghcr.io/codessa-platform/SERVICE_NAME
  newTag: v1.0.0

configMapGenerator:
- name: app-config
  literals:
  - NODE_ENV=production
  - LOG_LEVEL=info
  - API_URL=https://api.codessa.dev
```

## Monitoring and Observability

### Prometheus Metrics

```yaml
# k8s/monitoring/servicemonitor.yml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: SERVICE_NAME
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: SERVICE_NAME
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "SERVICE_NAME Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{service=\"SERVICE_NAME\"}[5m])"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service=\"SERVICE_NAME\"}[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{service=\"SERVICE_NAME\",status=~\"5..\"}[5m])"
          }
        ]
      }
    ]
  }
}
```

## Testing Strategy

### Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── services/
│   ├── controllers/
│   └── utils/
├── integration/          # Integration tests
│   ├── api/
│   ├── database/
│   └── external/
├── e2e/                  # End-to-end tests
│   ├── user-flows/
│   └── api-flows/
├── smoke/                # Smoke tests
│   └── health-checks/
├── production/           # Production tests
│   └── monitoring/
└── load/                 # Load tests
    └── scenarios/
```

### Jest Configuration

```javascript
// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: [
    '**/tests/**/*.test.(ts|js)',
    '**/__tests__/**/*.(ts|js)'
  ],
  collectCoverageFrom: [
    'src/**/*.{ts,js}',
    '!src/**/*.d.ts',
    '!src/index.ts'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  testTimeout: 10000
};
```

## Security Configuration

### Snyk Configuration

```yaml
# .snyk
version: v1.0.0
ignore: {}
patch: {}
language-settings:
  javascript:
    ignoreDevDependencies: true
```

### SonarCloud Configuration

```properties
# sonar-project.properties
sonar.projectKey=codessa-platform_SERVICE_NAME
sonar.organization=codessa-platform
sonar.sources=src
sonar.tests=tests
sonar.javascript.lcov.reportPaths=coverage/lcov.info
sonar.coverage.exclusions=**/*.test.ts,**/*.spec.ts
```

## Troubleshooting

### Common Issues

#### 1. Docker Build Failures
```bash
# Check Docker build context
docker build --no-cache -t test-build .

# Debug multi-stage builds
docker build --target builder -t debug-build .
docker run -it debug-build sh
```

#### 2. Kubernetes Deployment Issues
```bash
# Check pod status
kubectl get pods -n staging
kubectl describe pod POD_NAME -n staging
kubectl logs POD_NAME -n staging

# Check deployment status
kubectl rollout status deployment/SERVICE_NAME -n staging
```

#### 3. Test Failures
```bash
# Run tests with verbose output
npm test -- --verbose

# Run specific test suite
npm test -- --testPathPattern=integration

# Debug test environment
NODE_ENV=test npm test
```

### Performance Optimization

#### 1. Build Optimization
```yaml
# Use build cache
- name: Build with cache
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

#### 2. Parallel Jobs
```yaml
# Run jobs in parallel
jobs:
  test:
    strategy:
      matrix:
        node-version: [16, 18, 20]
      fail-fast: false
```

#### 3. Conditional Execution
```yaml
# Skip unnecessary steps
- name: Run integration tests
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: npm run test:integration
```

## Migration Checklist

### Pre-Migration
- [ ] Choose appropriate template
- [ ] Configure repository secrets
- [ ] Update package.json scripts
- [ ] Create Dockerfile
- [ ] Set up Kubernetes manifests
- [ ] Configure monitoring

### Migration
- [ ] Copy workflow template
- [ ] Customize for service
- [ ] Test in feature branch
- [ ] Verify all jobs pass
- [ ] Deploy to staging
- [ ] Run smoke tests

### Post-Migration
- [ ] Monitor deployment
- [ ] Verify metrics collection
- [ ] Update documentation
- [ ] Train team on new workflow
- [ ] Set up alerts

## Best Practices

### 1. Security
- Use least privilege access
- Scan for vulnerabilities regularly
- Keep dependencies updated
- Use secrets management
- Enable branch protection

### 2. Performance
- Use build caching
- Optimize Docker layers
- Run tests in parallel
- Use conditional execution
- Monitor build times

### 3. Reliability
- Implement proper health checks
- Use rolling deployments
- Set up monitoring and alerts
- Have rollback procedures
- Test disaster recovery

### 4. Maintainability
- Keep workflows DRY
- Use reusable actions
- Document customizations
- Version control everything
- Regular template updates

## Support

For questions or issues with CI/CD setup:

- 📧 Email: devops@codessa.dev
- 💬 Slack: #devops-support
- 📖 Documentation: [docs.codessa.dev/cicd](https://docs.codessa.dev/cicd)
- 🐛 Issues: [GitHub Issues](https://github.com/codessa-platform/platform-tools/issues)