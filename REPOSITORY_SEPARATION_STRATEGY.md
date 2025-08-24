# Repository Separation Strategy

## Overview
This document outlines the comprehensive strategy for separating the Codessa Platform monorepo into independent, manageable repositories while preserving git history, maintaining dependencies, and ensuring smooth transitions.

## Separation Objectives

### Primary Goals
1. **Independent Development**: Enable teams to work on services independently
2. **Scalable CI/CD**: Implement service-specific build and deployment pipelines
3. **Version Control**: Allow independent versioning and release cycles
4. **Access Control**: Implement granular permissions per repository
5. **History Preservation**: Maintain complete git history for each service

### Success Criteria
- ✅ Each service has its own repository with full git history
- ✅ All inter-service dependencies are properly configured
- ✅ CI/CD pipelines are functional for each repository
- ✅ Documentation is complete and accessible
- ✅ Development workflows are established

## Repository Structure Plan

### Target Repository Organization

```
GitHub Organization: codessa-platform
├── codessa-core                 # Foundation service
├── codessa-memory              # Memory management
├── codessa-llm-router          # LLM orchestration
├── codessa-metamind            # Meta-intelligence
├── devgenie                    # Development assistant
├── echoforge                   # Multi-agent framework
├── echopilot                   # User interface
├── pondskipperhq              # Management dashboard
├── gitguard                    # Security service
├── docfoundry                  # Documentation service
├── skyforge                    # Infrastructure automation
├── codessa-oss-starter        # Open source starter
├── aetherion-soulforge        # Specialized service
├── vosa-dev                   # Development tools
├── platform-tools             # Shared tooling
└── platform-docs             # Platform documentation
```

### Repository Naming Convention

```yaml
Naming Standards:
  Format: "codessa-{service-name}"
  Examples:
    - codessa-core
    - codessa-memory
    - codessa-llm-router
  
  Exceptions:
    - devgenie (established brand)
    - echoforge (established brand)
    - echopilot (established brand)
    - pondskipperhq (established brand)
    - gitguard (established brand)
    - docfoundry (established brand)
    - skyforge (established brand)
```

## Separation Process

### Phase 1: Preparation

#### 1.1 Repository Analysis
```bash
# Analyze current repository structure
git log --oneline --name-only | grep -E '^(codessa-core|devgenie|echoforge)/' | head -100

# Check file sizes and history
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print substr($0,6)}' | sort -n
```

#### 1.2 Dependency Mapping
```yaml
Dependency Analysis:
  - Code dependencies (imports, requires)
  - Configuration dependencies
  - Database schema dependencies
  - Asset dependencies (images, docs)
  - Build dependencies (shared scripts)
```

#### 1.3 Shared Resource Identification
```yaml
Shared Resources:
  Documentation:
    - README templates
    - Contributing guidelines
    - Code of conduct
  
  Configuration:
    - ESLint configs
    - Prettier configs
    - TypeScript configs
  
  Scripts:
    - Build scripts
    - Deployment scripts
    - Testing utilities
  
  Assets:
    - Logos and branding
    - Shared images
    - Documentation assets
```

### Phase 2: Repository Creation

#### 2.1 Git History Preservation

```bash
#!/bin/bash
# Script: extract-service-history.sh
# Usage: ./extract-service-history.sh <service-name> <source-repo> <target-repo>

SERVICE_NAME=$1
SOURCE_REPO=$2
TARGET_REPO=$3

# Clone source repository
git clone $SOURCE_REPO temp-$SERVICE_NAME
cd temp-$SERVICE_NAME

# Filter history for specific service
git filter-branch --prune-empty --subdirectory-filter $SERVICE_NAME -- --all

# Clean up
git reset --hard
git gc --aggressive
git prune

# Push to new repository
git remote add new-origin $TARGET_REPO
git push new-origin --all
git push new-origin --tags

# Cleanup
cd ..
rm -rf temp-$SERVICE_NAME
```

#### 2.2 Repository Template Setup

```yaml
# .github/repository-template.yml
name: "Codessa Service Template"
description: "Template for Codessa Platform services"

files:
  - ".github/workflows/ci.yml"
  - ".github/workflows/cd.yml"
  - ".github/ISSUE_TEMPLATE/"
  - ".github/PULL_REQUEST_TEMPLATE.md"
  - ".gitignore"
  - "README.md"
  - "CONTRIBUTING.md"
  - "LICENSE"
  - "package.json"
  - "Dockerfile"
  - "docker-compose.yml"
  - "k8s/"
```

### Phase 3: Service-Specific Setup

#### 3.1 Core Service (codessa-core)

```yaml
Repository: codessa-platform/codessa-core
Priority: HIGHEST (Foundation service)

Setup Steps:
  1. Extract core service files
  2. Set up authentication system
  3. Configure database connections
  4. Implement health checks
  5. Set up monitoring
  6. Create API documentation

Special Considerations:
  - Must be deployed first
  - Requires database migration scripts
  - Needs comprehensive testing
  - Critical for all other services
```

```dockerfile
# codessa-core/Dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

EXPOSE 3000
CMD ["npm", "start"]
```

#### 3.2 Memory Service (codessa-memory)

```yaml
Repository: codessa-platform/codessa-memory
Dependencies: [codessa-core]

Setup Steps:
  1. Extract memory service files
  2. Configure vector database connections
  3. Set up Redis caching
  4. Implement memory APIs
  5. Add performance monitoring
  6. Create backup strategies

Special Considerations:
  - Large data handling
  - Vector database integration
  - Performance critical
  - Backup and recovery
```

#### 3.3 LLM Router (codessa-llm-router)

```yaml
Repository: codessa-platform/codessa-llm-router
Dependencies: [codessa-core, codessa-memory]

Setup Steps:
  1. Extract LLM router files
  2. Configure multiple LLM providers
  3. Implement load balancing
  4. Set up cost tracking
  5. Add failover mechanisms
  6. Create provider management

Special Considerations:
  - Multiple API integrations
  - Cost optimization
  - Rate limiting
  - Provider failover
```

### Phase 4: CI/CD Pipeline Setup

#### 4.1 Standard CI Pipeline

```yaml
# .github/workflows/ci.yml
name: Continuous Integration

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        node-version: [16.x, 18.x, 20.x]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run linting
      run: npm run lint
    
    - name: Run type checking
      run: npm run type-check
    
    - name: Run tests
      run: npm run test:coverage
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage/lcov.info
    
    - name: Run security audit
      run: npm audit --audit-level=moderate
    
    - name: Build application
      run: npm run build

  docker:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

#### 4.2 Deployment Pipeline

```yaml
# .github/workflows/cd.yml
name: Continuous Deployment

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Deploy to staging
      run: |
        kubectl set image deployment/${{ github.event.repository.name }} \
          app=ghcr.io/${{ github.repository }}:${{ github.sha }} \
          --namespace=staging
    
    - name: Wait for deployment
      run: |
        kubectl rollout status deployment/${{ github.event.repository.name }} \
          --namespace=staging --timeout=300s
    
    - name: Run smoke tests
      run: npm run test:smoke -- --env=staging

  deploy-production:
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    environment: production
    needs: [deploy-staging]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Deploy to production
      run: |
        kubectl set image deployment/${{ github.event.repository.name }} \
          app=ghcr.io/${{ github.repository }}:${{ github.ref_name }} \
          --namespace=production
    
    - name: Wait for deployment
      run: |
        kubectl rollout status deployment/${{ github.event.repository.name }} \
          --namespace=production --timeout=600s
    
    - name: Run production tests
      run: npm run test:production
    
    - name: Notify deployment
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: "🚀 ${{ github.event.repository.name }} ${{ github.ref_name }} deployed to production"
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### Phase 5: Documentation Setup

#### 5.1 Repository README Template

```markdown
# {Service Name}

[![CI](https://github.com/codessa-platform/{repo-name}/workflows/CI/badge.svg)](https://github.com/codessa-platform/{repo-name}/actions)
[![Coverage](https://codecov.io/gh/codessa-platform/{repo-name}/branch/main/graph/badge.svg)](https://codecov.io/gh/codessa-platform/{repo-name})
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview
{Service description and purpose}

## Features
- Feature 1
- Feature 2
- Feature 3

## Quick Start

### Prerequisites
- Node.js 18+
- Docker
- {Other requirements}

### Installation
```bash
# Clone the repository
git clone https://github.com/codessa-platform/{repo-name}.git
cd {repo-name}

# Install dependencies
npm install

# Set up environment
cp .env.example .env

# Start development server
npm run dev
```

### Docker
```bash
# Build and run with Docker
docker build -t {service-name} .
docker run -p 3000:3000 {service-name}

# Or use docker-compose
docker-compose up
```

## API Documentation

API documentation is available at `/api/docs` when running the service.

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|----------|
| PORT | Server port | 3000 |
| NODE_ENV | Environment | development |
| DATABASE_URL | Database connection | - |

## Development

### Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run test` - Run tests
- `npm run lint` - Run linting
- `npm run type-check` - Run type checking

### Testing
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## Deployment

### Kubernetes
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app={service-name}
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [codessa-core](https://github.com/codessa-platform/codessa-core) - Core platform services
- [Platform Documentation](https://github.com/codessa-platform/platform-docs) - Complete platform docs

## Support

- 📧 Email: support@codessa.dev
- 💬 Discord: [Codessa Community](https://discord.gg/codessa)
- 📖 Documentation: [docs.codessa.dev](https://docs.codessa.dev)
```

### Phase 6: Migration Execution

#### 6.1 Migration Checklist

```yaml
Pre-Migration:
  - [ ] Backup current repository
  - [ ] Document current dependencies
  - [ ] Notify development team
  - [ ] Prepare rollback plan
  - [ ] Set up new repositories

Migration:
  - [ ] Extract service with history
  - [ ] Set up CI/CD pipelines
  - [ ] Configure dependencies
  - [ ] Update documentation
  - [ ] Test deployments

Post-Migration:
  - [ ] Verify all services work
  - [ ] Update team access
  - [ ] Update documentation links
  - [ ] Monitor for issues
  - [ ] Clean up old repository
```

#### 6.2 Migration Script

```bash
#!/bin/bash
# migrate-service.sh - Automated service migration

set -e

SERVICE_NAME=$1
ORG_NAME="codessa-platform"
SOURCE_REPO="https://github.com/$ORG_NAME/codessa-platform.git"

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: $0 <service-name>"
    exit 1
fi

echo "🚀 Starting migration for $SERVICE_NAME"

# Step 1: Create new repository
echo "📁 Creating new repository..."
gh repo create "$ORG_NAME/$SERVICE_NAME" --public --description "Codessa Platform - $SERVICE_NAME service"

# Step 2: Extract service history
echo "📜 Extracting git history..."
git clone $SOURCE_REPO temp-migration
cd temp-migration

# Filter for service directory
git filter-branch --prune-empty --subdirectory-filter $SERVICE_NAME -- --all

# Step 3: Push to new repository
echo "⬆️ Pushing to new repository..."
git remote set-url origin "https://github.com/$ORG_NAME/$SERVICE_NAME.git"
git push origin --all
git push origin --tags

# Step 4: Set up repository
echo "⚙️ Setting up repository..."
cd ..
rm -rf temp-migration

git clone "https://github.com/$ORG_NAME/$SERVICE_NAME.git"
cd $SERVICE_NAME

# Copy template files
cp ../templates/.github/workflows/* .github/workflows/
cp ../templates/Dockerfile .
cp ../templates/docker-compose.yml .
cp ../templates/.gitignore .

# Commit template files
git add .
git commit -m "Add repository template files"
git push origin main

echo "✅ Migration completed for $SERVICE_NAME"
echo "🔗 Repository: https://github.com/$ORG_NAME/$SERVICE_NAME"
```

## Risk Mitigation

### Potential Risks

1. **Git History Loss**
   - Mitigation: Use `git filter-branch` with proper testing
   - Backup: Keep original repository as backup

2. **Dependency Breakage**
   - Mitigation: Gradual migration with dependency mapping
   - Testing: Comprehensive integration testing

3. **CI/CD Pipeline Failures**
   - Mitigation: Test pipelines in staging environment
   - Rollback: Keep old pipelines until new ones are stable

4. **Team Disruption**
   - Mitigation: Clear communication and training
   - Support: Dedicated migration support team

### Rollback Plan

```yaml
Rollback Triggers:
  - Critical service failures
  - Major dependency issues
  - Team productivity impact
  - Security vulnerabilities

Rollback Steps:
  1. Revert DNS/routing to old services
  2. Restore database connections
  3. Reactivate old CI/CD pipelines
  4. Notify team of rollback
  5. Investigate and fix issues
  6. Plan re-migration
```

## Success Metrics

### Technical Metrics
- **Migration Time**: < 2 hours per service
- **History Preservation**: 100% git history retained
- **Pipeline Success**: 95% CI/CD success rate
- **Deployment Time**: < 30 minutes per service

### Business Metrics
- **Developer Productivity**: No decrease during migration
- **System Uptime**: 99.9% during migration
- **Team Satisfaction**: > 80% positive feedback
- **Time to Market**: No impact on feature delivery

## Timeline

### Week 1: Preparation
- Repository analysis
- Template creation
- Team training
- Tool setup

### Week 2-3: Core Services
- codessa-core migration
- codessa-memory migration
- codessa-llm-router migration
- Testing and validation

### Week 4-5: Application Services
- devgenie migration
- echoforge migration
- docfoundry migration
- Integration testing

### Week 6: Interface Services
- echopilot migration
- pondskipperhq migration
- End-to-end testing
- Documentation updates

### Week 7: Cleanup
- Old repository cleanup
- Final testing
- Team feedback
- Process documentation

## Conclusion

This repository separation strategy provides a comprehensive approach to transforming the Codessa Platform from a monorepo to a distributed architecture. The strategy emphasizes:

1. **Minimal Disruption**: Gradual migration with proper testing
2. **History Preservation**: Complete git history for each service
3. **Automation**: Scripted migration process
4. **Quality Assurance**: Comprehensive testing at each step
5. **Risk Management**: Clear rollback procedures

Successful execution of this strategy will result in a more scalable, maintainable, and developer-friendly platform architecture.