# Codessa Platform - Project Structure Guide

## Overview

This guide defines the optimal project structure for all Codessa Platform services, ensuring consistent organization, maintainability, and scalability across the entire ecosystem.

## Design Principles

### 1. Separation of Concerns
- **Domain Logic**: Business rules and core functionality
- **Infrastructure**: External dependencies and technical concerns
- **Presentation**: User interfaces and API endpoints
- **Configuration**: Environment-specific settings

### 2. Layered Architecture
- **Presentation Layer**: Controllers, routes, middleware
- **Application Layer**: Use cases, services, orchestration
- **Domain Layer**: Entities, value objects, domain services
- **Infrastructure Layer**: Repositories, external services, databases

### 3. Dependency Direction
- Dependencies flow inward toward the domain
- Domain layer has no external dependencies
- Infrastructure depends on domain, not vice versa

## Universal Structure Template

```
project-name/
├── src/                          # Source code
│   ├── api/                      # API layer (REST/GraphQL)
│   │   ├── controllers/          # Request handlers
│   │   ├── middleware/           # Request/response middleware
│   │   ├── routes/               # Route definitions
│   │   ├── validators/           # Input validation schemas
│   │   └── serializers/          # Response formatting
│   ├── application/              # Application services
│   │   ├── services/             # Business logic orchestration
│   │   ├── use-cases/            # Specific business operations
│   │   ├── commands/             # Command handlers (CQRS)
│   │   ├── queries/              # Query handlers (CQRS)
│   │   └── events/               # Event handlers
│   ├── domain/                   # Core business logic
│   │   ├── entities/             # Business entities
│   │   ├── value-objects/        # Immutable value types
│   │   ├── repositories/         # Repository interfaces
│   │   ├── services/             # Domain services
│   │   └── events/               # Domain events
│   ├── infrastructure/           # External concerns
│   │   ├── database/             # Database implementations
│   │   │   ├── repositories/     # Repository implementations
│   │   │   ├── migrations/       # Database migrations
│   │   │   └── seeds/            # Test data
│   │   ├── external/             # External service clients
│   │   ├── messaging/            # Message queues, pub/sub
│   │   ├── storage/              # File storage, caching
│   │   └── monitoring/           # Logging, metrics, tracing
│   ├── shared/                   # Shared utilities
│   │   ├── types/                # TypeScript type definitions
│   │   ├── utils/                # Helper functions
│   │   ├── constants/            # Application constants
│   │   ├── errors/               # Custom error classes
│   │   └── decorators/           # Custom decorators
│   ├── config/                   # Configuration
│   │   ├── database.ts           # Database configuration
│   │   ├── redis.ts              # Cache configuration
│   │   ├── auth.ts               # Authentication config
│   │   └── index.ts              # Main config aggregator
│   └── main.ts                   # Application entry point
├── tests/                        # Test files
│   ├── unit/                     # Unit tests
│   │   ├── domain/               # Domain logic tests
│   │   ├── application/          # Service tests
│   │   └── shared/               # Utility tests
│   ├── integration/              # Integration tests
│   │   ├── api/                  # API endpoint tests
│   │   ├── database/             # Database tests
│   │   └── external/             # External service tests
│   ├── e2e/                      # End-to-end tests
│   │   ├── scenarios/            # User journey tests
│   │   └── fixtures/             # Test data
│   ├── performance/              # Load and stress tests
│   ├── security/                 # Security tests
│   └── helpers/                  # Test utilities
├── docs/                         # Documentation
│   ├── api/                      # API documentation
│   ├── architecture/             # Architecture decisions
│   ├── deployment/               # Deployment guides
│   └── development/              # Development guides
├── scripts/                      # Build and utility scripts
│   ├── build/                    # Build scripts
│   ├── deploy/                   # Deployment scripts
│   ├── db/                       # Database scripts
│   └── dev/                      # Development utilities
├── k8s/                          # Kubernetes manifests
│   ├── base/                     # Base configurations
│   ├── staging/                  # Staging environment
│   └── production/               # Production environment
├── .github/                      # GitHub workflows
│   └── workflows/                # CI/CD pipelines
├── docker/                       # Docker configurations
│   ├── Dockerfile                # Main Dockerfile
│   ├── Dockerfile.dev            # Development Dockerfile
│   └── docker-compose.yml        # Local development
├── config/                       # External configurations
│   ├── nginx/                    # Nginx configurations
│   ├── prometheus/               # Monitoring configs
│   └── grafana/                  # Dashboard configs
├── package.json                  # Dependencies and scripts
├── tsconfig.json                 # TypeScript configuration
├── jest.config.js                # Test configuration
├── .eslintrc.js                  # Linting rules
├── .prettierrc                   # Code formatting
├── .env.example                  # Environment template
└── README.md                     # Project documentation
```

## Service-Specific Structures

### Node.js Backend Services

#### Codessa Core
```
codessa-core/
├── src/
│   ├── api/
│   │   ├── controllers/
│   │   │   ├── auth.controller.ts
│   │   │   ├── user.controller.ts
│   │   │   └── project.controller.ts
│   │   ├── middleware/
│   │   │   ├── auth.middleware.ts
│   │   │   ├── validation.middleware.ts
│   │   │   └── error.middleware.ts
│   │   ├── routes/
│   │   │   ├── auth.routes.ts
│   │   │   ├── user.routes.ts
│   │   │   └── index.ts
│   │   └── validators/
│   │       ├── auth.validator.ts
│   │       └── user.validator.ts
│   ├── application/
│   │   ├── services/
│   │   │   ├── auth.service.ts
│   │   │   ├── user.service.ts
│   │   │   └── project.service.ts
│   │   ├── use-cases/
│   │   │   ├── create-user.use-case.ts
│   │   │   ├── authenticate-user.use-case.ts
│   │   │   └── manage-project.use-case.ts
│   │   └── events/
│   │       ├── user-created.handler.ts
│   │       └── project-updated.handler.ts
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── user.entity.ts
│   │   │   ├── project.entity.ts
│   │   │   └── session.entity.ts
│   │   ├── value-objects/
│   │   │   ├── email.vo.ts
│   │   │   ├── password.vo.ts
│   │   │   └── project-id.vo.ts
│   │   ├── repositories/
│   │   │   ├── user.repository.ts
│   │   │   └── project.repository.ts
│   │   └── services/
│   │       ├── password.service.ts
│   │       └── token.service.ts
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── repositories/
│   │   │   │   ├── user.repository.impl.ts
│   │   │   │   └── project.repository.impl.ts
│   │   │   ├── migrations/
│   │   │   └── seeds/
│   │   ├── external/
│   │   │   ├── email.client.ts
│   │   │   └── storage.client.ts
│   │   └── messaging/
│   │       ├── event-bus.ts
│   │       └── queue.client.ts
│   ├── shared/
│   │   ├── types/
│   │   │   ├── api.types.ts
│   │   │   └── database.types.ts
│   │   ├── utils/
│   │   │   ├── crypto.util.ts
│   │   │   └── validation.util.ts
│   │   └── errors/
│   │       ├── domain.errors.ts
│   │       └── api.errors.ts
│   └── config/
│       ├── database.ts
│       ├── redis.ts
│       └── index.ts
└── tests/
    ├── unit/
    │   ├── domain/
    │   ├── application/
    │   └── shared/
    ├── integration/
    │   ├── api/
    │   └── database/
    └── e2e/
        └── scenarios/
```

#### Codessa LLM Router
```
codessa-llm-router/
├── src/
│   ├── api/
│   │   ├── controllers/
│   │   │   ├── routing.controller.ts
│   │   │   ├── models.controller.ts
│   │   │   └── health.controller.ts
│   │   ├── middleware/
│   │   │   ├── rate-limit.middleware.ts
│   │   │   ├── auth.middleware.ts
│   │   │   └── request-logging.middleware.ts
│   │   └── routes/
│   │       ├── v1/
│   │       │   ├── chat.routes.ts
│   │       │   ├── completions.routes.ts
│   │       │   └── models.routes.ts
│   │       └── index.ts
│   ├── application/
│   │   ├── services/
│   │   │   ├── routing.service.ts
│   │   │   ├── load-balancer.service.ts
│   │   │   └── model-registry.service.ts
│   │   ├── strategies/
│   │   │   ├── round-robin.strategy.ts
│   │   │   ├── weighted.strategy.ts
│   │   │   └── performance-based.strategy.ts
│   │   └── policies/
│   │       ├── retry.policy.ts
│   │       ├── timeout.policy.ts
│   │       └── circuit-breaker.policy.ts
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── model.entity.ts
│   │   │   ├── request.entity.ts
│   │   │   └── response.entity.ts
│   │   ├── value-objects/
│   │   │   ├── model-config.vo.ts
│   │   │   ├── routing-rule.vo.ts
│   │   │   └── performance-metrics.vo.ts
│   │   └── services/
│   │       ├── model-selector.service.ts
│   │       └── performance-tracker.service.ts
│   ├── infrastructure/
│   │   ├── providers/
│   │   │   ├── openai.provider.ts
│   │   │   ├── anthropic.provider.ts
│   │   │   ├── azure.provider.ts
│   │   │   └── local.provider.ts
│   │   ├── monitoring/
│   │   │   ├── metrics.collector.ts
│   │   │   ├── health-checker.ts
│   │   │   └── performance.tracker.ts
│   │   └── cache/
│   │       ├── redis.cache.ts
│   │       └── memory.cache.ts
│   └── shared/
│       ├── types/
│       │   ├── llm.types.ts
│       │   ├── routing.types.ts
│       │   └── metrics.types.ts
│       └── utils/
│           ├── token-counter.util.ts
│           └── response-parser.util.ts
└── tests/
    ├── unit/
    │   ├── strategies/
    │   ├── policies/
    │   └── providers/
    ├── integration/
    │   ├── providers/
    │   └── routing/
    └── load/
        └── scenarios/
```

### Python Services

#### Codessa Memory
```
codessa-memory/
├── src/
│   ├── api/
│   │   ├── controllers/
│   │   │   ├── memory_controller.py
│   │   │   ├── search_controller.py
│   │   │   └── health_controller.py
│   │   ├── middleware/
│   │   │   ├── auth_middleware.py
│   │   │   ├── cors_middleware.py
│   │   │   └── logging_middleware.py
│   │   ├── routes/
│   │   │   ├── v1/
│   │   │   │   ├── memory_routes.py
│   │   │   │   ├── search_routes.py
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   └── schemas/
│   │       ├── memory_schemas.py
│   │       ├── search_schemas.py
│   │       └── common_schemas.py
│   ├── application/
│   │   ├── services/
│   │   │   ├── memory_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── search_service.py
│   │   │   └── indexing_service.py
│   │   ├── use_cases/
│   │   │   ├── store_memory.py
│   │   │   ├── retrieve_memory.py
│   │   │   ├── search_memories.py
│   │   │   └── update_memory.py
│   │   └── handlers/
│   │       ├── memory_created_handler.py
│   │       └── memory_updated_handler.py
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── memory.py
│   │   │   ├── embedding.py
│   │   │   └── search_result.py
│   │   ├── value_objects/
│   │   │   ├── memory_id.py
│   │   │   ├── content_hash.py
│   │   │   └── similarity_score.py
│   │   ├── repositories/
│   │   │   ├── memory_repository.py
│   │   │   └── embedding_repository.py
│   │   └── services/
│   │       ├── similarity_service.py
│   │       └── clustering_service.py
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── repositories/
│   │   │   │   ├── postgres_memory_repository.py
│   │   │   │   └── redis_cache_repository.py
│   │   │   ├── migrations/
│   │   │   │   └── alembic/
│   │   │   └── models/
│   │   │       ├── memory_model.py
│   │   │       └── embedding_model.py
│   │   ├── vector_stores/
│   │   │   ├── pinecone_store.py
│   │   │   ├── weaviate_store.py
│   │   │   └── chroma_store.py
│   │   ├── ml_models/
│   │   │   ├── embedding_models/
│   │   │   │   ├── openai_embeddings.py
│   │   │   │   ├── sentence_transformers.py
│   │   │   │   └── custom_embeddings.py
│   │   │   └── clustering_models/
│   │   │       ├── kmeans_clustering.py
│   │   │       └── hierarchical_clustering.py
│   │   └── external/
│   │       ├── llm_clients/
│   │       │   ├── openai_client.py
│   │       │   └── anthropic_client.py
│   │       └── notification_client.py
│   ├── shared/
│   │   ├── types/
│   │   │   ├── memory_types.py
│   │   │   ├── embedding_types.py
│   │   │   └── search_types.py
│   │   ├── utils/
│   │   │   ├── text_processing.py
│   │   │   ├── vector_operations.py
│   │   │   └── validation.py
│   │   ├── constants/
│   │   │   ├── embedding_constants.py
│   │   │   └── search_constants.py
│   │   └── exceptions/
│   │       ├── memory_exceptions.py
│   │       └── search_exceptions.py
│   ├── config/
│   │   ├── database.py
│   │   ├── vector_store.py
│   │   ├── ml_models.py
│   │   └── settings.py
│   └── main.py
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/
│   │   ├── database/
│   │   ├── vector_stores/
│   │   └── ml_models/
│   ├── e2e/
│   │   └── scenarios/
│   └── performance/
│       ├── embedding_benchmarks.py
│       └── search_benchmarks.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   ├── test.txt
│   └── prod.txt
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
└── pyproject.toml
```

### React Frontend Services

#### EchoPilot
```
echopilot/
├── public/
│   ├── index.html
│   ├── manifest.json
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Button.test.tsx
│   │   │   │   ├── Button.stories.tsx
│   │   │   │   └── Button.module.css
│   │   │   ├── Input/
│   │   │   ├── Modal/
│   │   │   └── Layout/
│   │   ├── features/
│   │   │   ├── chat/
│   │   │   │   ├── ChatWindow/
│   │   │   │   ├── MessageList/
│   │   │   │   ├── MessageInput/
│   │   │   │   └── ChatHistory/
│   │   │   ├── projects/
│   │   │   │   ├── ProjectList/
│   │   │   │   ├── ProjectCard/
│   │   │   │   └── ProjectForm/
│   │   │   └── settings/
│   │   │       ├── UserSettings/
│   │   │       ├── ModelSettings/
│   │   │       └── IntegrationSettings/
│   │   └── pages/
│   │       ├── HomePage/
│   │       ├── ChatPage/
│   │       ├── ProjectsPage/
│   │       └── SettingsPage/
│   ├── hooks/
│   │   ├── useChat.ts
│   │   ├── useProjects.ts
│   │   ├── useAuth.ts
│   │   ├── useWebSocket.ts
│   │   └── useLocalStorage.ts
│   ├── services/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── auth.api.ts
│   │   │   ├── chat.api.ts
│   │   │   ├── projects.api.ts
│   │   │   └── settings.api.ts
│   │   ├── websocket/
│   │   │   ├── websocket.service.ts
│   │   │   └── message.handlers.ts
│   │   └── storage/
│   │       ├── local-storage.service.ts
│   │       └── session-storage.service.ts
│   ├── store/
│   │   ├── slices/
│   │   │   ├── auth.slice.ts
│   │   │   ├── chat.slice.ts
│   │   │   ├── projects.slice.ts
│   │   │   └── ui.slice.ts
│   │   ├── middleware/
│   │   │   ├── api.middleware.ts
│   │   │   └── persistence.middleware.ts
│   │   ├── selectors/
│   │   │   ├── auth.selectors.ts
│   │   │   ├── chat.selectors.ts
│   │   │   └── projects.selectors.ts
│   │   └── store.ts
│   ├── utils/
│   │   ├── formatting/
│   │   │   ├── date.utils.ts
│   │   │   ├── text.utils.ts
│   │   │   └── number.utils.ts
│   │   ├── validation/
│   │   │   ├── form.validators.ts
│   │   │   └── api.validators.ts
│   │   ├── constants/
│   │   │   ├── api.constants.ts
│   │   │   ├── ui.constants.ts
│   │   │   └── app.constants.ts
│   │   └── helpers/
│   │       ├── error.helpers.ts
│   │       └── async.helpers.ts
│   ├── types/
│   │   ├── api.types.ts
│   │   ├── chat.types.ts
│   │   ├── project.types.ts
│   │   ├── user.types.ts
│   │   └── common.types.ts
│   ├── styles/
│   │   ├── globals.css
│   │   ├── variables.css
│   │   ├── components.css
│   │   └── utilities.css
│   ├── assets/
│   │   ├── images/
│   │   ├── icons/
│   │   └── fonts/
│   ├── config/
│   │   ├── api.config.ts
│   │   ├── app.config.ts
│   │   └── theme.config.ts
│   ├── App.tsx
│   ├── App.test.tsx
│   ├── index.tsx
│   └── setupTests.ts
├── tests/
│   ├── unit/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── utils/
│   ├── integration/
│   │   ├── api/
│   │   └── store/
│   ├── e2e/
│   │   ├── specs/
│   │   ├── fixtures/
│   │   └── support/
│   └── visual/
│       ├── screenshots/
│       └── stories/
├── .storybook/
│   ├── main.js
│   ├── preview.js
│   └── addons.js
├── cypress/
│   ├── e2e/
│   ├── fixtures/
│   ├── support/
│   └── cypress.config.ts
├── playwright/
│   ├── tests/
│   ├── fixtures/
│   └── playwright.config.ts
└── package.json
```

## File Naming Conventions

### TypeScript/JavaScript
- **Files**: `kebab-case.ts` or `camelCase.ts`
- **Classes**: `PascalCase.ts`
- **Components**: `PascalCase.tsx`
- **Hooks**: `useCamelCase.ts`
- **Types**: `camelCase.types.ts`
- **Constants**: `UPPER_SNAKE_CASE.ts`

### Python
- **Files**: `snake_case.py`
- **Classes**: `PascalCase` (in `snake_case.py` files)
- **Modules**: `snake_case.py`
- **Constants**: `UPPER_SNAKE_CASE.py`

### Configuration Files
- **Environment**: `.env.example`, `.env.local`
- **Docker**: `Dockerfile`, `docker-compose.yml`
- **Kubernetes**: `deployment.yml`, `service.yml`
- **CI/CD**: `ci-cd.yml`, `deploy.yml`

## Directory Organization Rules

### 1. Grouping Strategy
- **By Feature**: Group related functionality together
- **By Layer**: Separate concerns by architectural layer
- **By Type**: Group similar file types when appropriate

### 2. Depth Limits
- **Maximum 4 levels deep** for source directories
- **Use index files** to simplify imports
- **Flatten when possible** without losing organization

### 3. Import Organization
```typescript
// 1. External libraries
import express from 'express';
import { Request, Response } from 'express';

// 2. Internal modules (absolute paths)
import { UserService } from '@/application/services/user.service';
import { User } from '@/domain/entities/user.entity';

// 3. Relative imports
import { validateRequest } from '../middleware/validation.middleware';
import { UserController } from './user.controller';

// 4. Type-only imports (last)
import type { UserCreateRequest } from '@/shared/types/api.types';
```

## Configuration Management

### Environment Variables
```typescript
// config/index.ts
export const config = {
  app: {
    name: process.env.APP_NAME || 'codessa-service',
    version: process.env.APP_VERSION || '1.0.0',
    port: parseInt(process.env.PORT || '3000'),
    env: process.env.NODE_ENV || 'development',
  },
  database: {
    url: process.env.DATABASE_URL!,
    maxConnections: parseInt(process.env.DB_MAX_CONNECTIONS || '10'),
    ssl: process.env.DB_SSL === 'true',
  },
  redis: {
    url: process.env.REDIS_URL!,
    ttl: parseInt(process.env.REDIS_TTL || '3600'),
  },
  auth: {
    jwtSecret: process.env.JWT_SECRET!,
    jwtExpiry: process.env.JWT_EXPIRY || '24h',
    bcryptRounds: parseInt(process.env.BCRYPT_ROUNDS || '12'),
  },
  external: {
    openaiApiKey: process.env.OPENAI_API_KEY,
    anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  },
  monitoring: {
    logLevel: process.env.LOG_LEVEL || 'info',
    metricsEnabled: process.env.METRICS_ENABLED === 'true',
    tracingEnabled: process.env.TRACING_ENABLED === 'true',
  },
};
```

### Configuration Validation
```typescript
// config/validation.ts
import Joi from 'joi';

const configSchema = Joi.object({
  app: Joi.object({
    name: Joi.string().required(),
    version: Joi.string().required(),
    port: Joi.number().port().required(),
    env: Joi.string().valid('development', 'staging', 'production').required(),
  }).required(),
  database: Joi.object({
    url: Joi.string().uri().required(),
    maxConnections: Joi.number().positive().required(),
    ssl: Joi.boolean().required(),
  }).required(),
  // ... other validations
});

export const validateConfig = (config: any) => {
  const { error, value } = configSchema.validate(config);
  if (error) {
    throw new Error(`Configuration validation error: ${error.message}`);
  }
  return value;
};
```

## Testing Structure

### Test Organization
```
tests/
├── unit/                     # Fast, isolated tests
│   ├── domain/               # Business logic tests
│   │   ├── entities/
│   │   ├── value-objects/
│   │   └── services/
│   ├── application/          # Service layer tests
│   │   ├── services/
│   │   └── use-cases/
│   └── shared/               # Utility tests
│       ├── utils/
│       └── validators/
├── integration/              # Component interaction tests
│   ├── api/                  # API endpoint tests
│   │   ├── auth/
│   │   ├── users/
│   │   └── projects/
│   ├── database/             # Database integration tests
│   │   ├── repositories/
│   │   └── migrations/
│   └── external/             # External service tests
│       ├── email/
│       └── storage/
├── e2e/                      # End-to-end user scenarios
│   ├── scenarios/
│   │   ├── user-registration.test.ts
│   │   ├── project-creation.test.ts
│   │   └── chat-interaction.test.ts
│   ├── fixtures/
│   │   ├── users.json
│   │   └── projects.json
│   └── helpers/
│       ├── test-server.ts
│       └── database-helper.ts
├── performance/              # Load and stress tests
│   ├── load/
│   │   ├── api-load.test.ts
│   │   └── database-load.test.ts
│   └── stress/
│       ├── memory-stress.test.ts
│       └── cpu-stress.test.ts
├── security/                 # Security-focused tests
│   ├── auth/
│   │   ├── jwt-security.test.ts
│   │   └── password-security.test.ts
│   ├── api/
│   │   ├── input-validation.test.ts
│   │   └── rate-limiting.test.ts
│   └── dependencies/
│       └── vulnerability-scan.test.ts
└── helpers/                  # Test utilities
    ├── factories/
    │   ├── user.factory.ts
    │   └── project.factory.ts
    ├── mocks/
    │   ├── database.mock.ts
    │   └── external-api.mock.ts
    └── setup/
        ├── test-database.ts
        └── test-server.ts
```

### Test Naming Conventions
```typescript
// Unit tests
describe('UserService', () => {
  describe('createUser', () => {
    it('should create user with valid data', () => {});
    it('should throw error when email already exists', () => {});
    it('should hash password before saving', () => {});
  });
});

// Integration tests
describe('POST /api/v1/users', () => {
  it('should create user and return 201', () => {});
  it('should return 400 for invalid email', () => {});
  it('should return 409 for duplicate email', () => {});
});

// E2E tests
describe('User Registration Flow', () => {
  it('should allow new user to register and login', () => {});
  it('should send welcome email after registration', () => {});
});
```

## Documentation Structure

### API Documentation
```
docs/
├── api/
│   ├── openapi.yml           # OpenAPI specification
│   ├── authentication.md    # Auth documentation
│   ├── endpoints/
│   │   ├── users.md
│   │   ├── projects.md
│   │   └── chat.md
│   └── examples/
│       ├── requests/
│       └── responses/
├── architecture/
│   ├── overview.md
│   ├── decisions/
│   │   ├── 001-database-choice.md
│   │   ├── 002-authentication-strategy.md
│   │   └── 003-caching-approach.md
│   └── diagrams/
│       ├── system-architecture.png
│       └── data-flow.png
├── deployment/
│   ├── local-development.md
│   ├── staging-deployment.md
│   ├── production-deployment.md
│   └── troubleshooting.md
└── development/
    ├── getting-started.md
    ├── coding-standards.md
    ├── testing-guide.md
    └── contributing.md
```

## Build and Deployment

### Build Scripts Structure
```
scripts/
├── build/
│   ├── build.sh             # Main build script
│   ├── build-docker.sh      # Docker build script
│   ├── build-assets.sh      # Asset compilation
│   └── validate-build.sh    # Build validation
├── deploy/
│   ├── deploy-staging.sh    # Staging deployment
│   ├── deploy-production.sh # Production deployment
│   ├── rollback.sh          # Rollback script
│   └── health-check.sh      # Post-deployment checks
├── db/
│   ├── migrate.sh           # Database migrations
│   ├── seed.sh              # Database seeding
│   ├── backup.sh            # Database backup
│   └── restore.sh           # Database restore
└── dev/
    ├── setup.sh             # Development setup
    ├── reset.sh             # Reset development environment
    ├── lint.sh              # Code linting
    └── test.sh              # Test execution
```

## Monitoring and Observability

### Logging Structure
```typescript
// infrastructure/monitoring/logger.ts
import winston from 'winston';

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: process.env.SERVICE_NAME || 'codessa-service',
    version: process.env.SERVICE_VERSION || '1.0.0',
  },
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      ),
    }),
  ],
});

export { logger };
```

### Metrics Collection
```typescript
// infrastructure/monitoring/metrics.ts
import { register, Counter, Histogram, Gauge } from 'prom-client';

export const httpRequestsTotal = new Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status'],
});

export const httpRequestDuration = new Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route'],
  buckets: [0.1, 0.5, 1, 2, 5],
});

export const activeConnections = new Gauge({
  name: 'active_connections',
  help: 'Number of active connections',
});

// Register metrics
register.registerMetric(httpRequestsTotal);
register.registerMetric(httpRequestDuration);
register.registerMetric(activeConnections);
```

## Migration Strategy

### Phase 1: Structure Setup
1. Create directory structure for each service
2. Move existing files to appropriate locations
3. Update import paths and references
4. Ensure all tests still pass

### Phase 2: Refactoring
1. Extract domain logic from infrastructure
2. Implement repository pattern
3. Separate business logic from API controllers
4. Add proper error handling and validation

### Phase 3: Enhancement
1. Add comprehensive testing
2. Implement monitoring and logging
3. Add documentation
4. Set up CI/CD pipelines

### Phase 4: Optimization
1. Performance tuning
2. Security hardening
3. Scalability improvements
4. Monitoring and alerting

## Best Practices

### 1. Code Organization
- Keep related files together
- Use consistent naming conventions
- Implement proper separation of concerns
- Follow SOLID principles

### 2. Dependency Management
- Use dependency injection
- Avoid circular dependencies
- Keep dependencies explicit
- Use interfaces for abstractions

### 3. Error Handling
- Use custom error classes
- Implement proper error boundaries
- Log errors with context
- Provide meaningful error messages

### 4. Testing
- Write tests first (TDD)
- Maintain high test coverage
- Use appropriate test types
- Keep tests fast and reliable

### 5. Documentation
- Document public APIs
- Keep documentation up to date
- Use code comments sparingly
- Provide examples and guides

## Conclusion

This project structure guide provides a solid foundation for organizing Codessa Platform services. It ensures consistency, maintainability, and scalability across all projects while following industry best practices and architectural principles.

Regular reviews and updates of this structure will help maintain its effectiveness as the platform evolves and grows.