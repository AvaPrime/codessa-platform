# Multi-Agent Factory Authentication System

This document describes the production-ready authentication system implemented for the Multi-Agent Factory project.

## Overview

The authentication system provides:
- JWT-based authentication with secure token management
- Role-based access control (RBAC) with granular permissions
- User management with password security and account lockout
- Multi-factor authentication (MFA) support with TOTP
- Session management and token blacklisting
- Comprehensive audit logging
- Database-backed user storage with PostgreSQL
- Redis caching for performance and session management

## Architecture

### Components

1. **Authentication Module** (`api/auth.py`)
   - JWT token creation and verification
   - Role-based permission checking
   - Token blacklisting with Redis
   - Security hardening features

2. **Database Models** (`api/models.py`)
   - SQLAlchemy models for users, roles, and sessions
   - Pydantic models for API validation
   - Password strength validation

3. **User Service** (`api/user_service.py`)
   - User management operations
   - Authentication logic with security features
   - MFA setup and verification
   - Audit logging

4. **Database Layer** (`api/database.py`)
   - SQLAlchemy setup and session management
   - Database health checks
   - Connection pooling

## Database Schema

### Tables

- **users**: Core user information
- **roles**: Available roles and permissions
- **user_roles**: Many-to-many relationship between users and roles
- **user_sessions**: Active user sessions for tracking and invalidation

### Default Roles

- **admin**: Full system access
- **operator**: Task and user management
- **viewer**: Read-only access
- **agent-***: Specialized agent roles (research, analysis, synthesis, validation, coordination)

## API Endpoints

### Authentication

- `POST /auth/login` - User login with credentials
- `POST /auth/logout` - User logout and session invalidation
- `POST /auth/change-password` - Change user password
- `POST /auth/setup-mfa` - Setup multi-factor authentication
- `POST /auth/enable-mfa` - Enable MFA after verification
- `POST /auth/disable-mfa` - Disable MFA

### User Management

- `POST /users` - Create new user (admin only)
- `GET /users` - List all users with pagination
- `GET /users/{user_id}` - Get user by ID
- `PUT /users/{user_id}` - Update user information
- `DELETE /users/{user_id}` - Soft delete user

### Role Management

- `POST /roles` - Create new role (admin only)
- `GET /roles` - List all roles
- `GET /roles/{role_id}` - Get role by ID
- `PUT /roles/{role_id}` - Update role
- `DELETE /roles/{role_id}` - Delete role

## Security Features

### Password Security

- Minimum 8 characters with complexity requirements
- Argon2 hashing with bcrypt fallback
- Password strength validation
- Password history prevention (future enhancement)

### Account Security

- Account lockout after 5 failed attempts
- 30-minute lockout duration
- Rate limiting on authentication endpoints
- Session timeout and invalidation

### Token Security

- JWT tokens with 24-hour expiration
- Token blacklisting on logout
- Secure token storage recommendations
- JTI (JWT ID) for unique token identification

### Multi-Factor Authentication

- TOTP-based MFA using authenticator apps
- QR code generation for easy setup
- Backup codes (future enhancement)
- MFA enforcement policies (configurable)

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Database Configuration
DATABASE_URL=postgresql://maf_user:maf_password@localhost:5432/maf_db

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Security Settings
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
PASSWORD_MIN_LENGTH=8
```

### Database Setup

1. **Initialize Database**:
   ```bash
   # Database tables are automatically created on startup
   # Or manually run:
   python -c "from api.database import create_tables; import asyncio; asyncio.run(create_tables())"
   ```

2. **Run Migrations** (if using Alembic):
   ```bash
   alembic upgrade head
   ```

3. **Create Initial Admin User**:
   The system creates a default admin user:
   - Username: `admin`
   - Password: `Admin123!@#`
   - **Change this password immediately in production!**

## Usage Examples

### Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!@#"
  }'
```

### Create User

```bash
curl -X POST "http://localhost:8000/users" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "SecurePass123!",
    "role_names": ["operator"]
  }'
```

### Setup MFA

```bash
curl -X POST "http://localhost:8000/auth/setup-mfa" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Permissions System

### Permission Scopes

- `tasks:create`, `tasks:read`, `tasks:delete`
- `results:create`, `results:read`, `results:delete`
- `users:read`, `users:write`, `users:delete`
- `admin:read`, `admin:write`, `admin:delete`
- `system:health`, `system:metrics`
- `ingest:create`, `ingest:read`

### Role Permissions Matrix

| Role | Tasks | Results | Users | Admin | System | Ingest |
|------|-------|---------|-------|-------|--------|---------|
| admin | CRD | CRD | CRD | CRD | RW | CR |
| operator | CR | R | R | - | R | C |
| viewer | R | R | - | - | R | - |
| agent-* | R | C | - | - | R | - |

*Legend: C=Create, R=Read, U=Update, D=Delete*

## Monitoring and Logging

### Audit Events

- User login/logout attempts
- Password changes
- MFA setup/changes
- User creation/modification
- Role assignments
- Failed authentication attempts

### Metrics

- Authentication success/failure rates
- Active user sessions
- MFA adoption rates
- Account lockout incidents

## Security Best Practices

### Deployment

1. **Change Default Credentials**: Update the default admin password
2. **Secure JWT Secret**: Use a strong, randomly generated JWT secret
3. **HTTPS Only**: Always use HTTPS in production
4. **Database Security**: Secure database connections and credentials
5. **Redis Security**: Secure Redis instance and connections

### Operational

1. **Regular Password Updates**: Enforce password rotation policies
2. **Monitor Failed Logins**: Set up alerts for suspicious activity
3. **Session Management**: Regular cleanup of expired sessions
4. **Backup Strategy**: Regular backups of user data and audit logs

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check database credentials and connectivity
   - Verify database tables are created

2. **Redis Connection Errors**
   - Verify Redis is running and accessible
   - Check Redis configuration

3. **JWT Token Issues**
   - Verify JWT secret is consistent
   - Check token expiration settings

4. **Permission Denied Errors**
   - Verify user roles and permissions
   - Check scope requirements on endpoints

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('api.auth').setLevel(logging.DEBUG)
logging.getLogger('api.user_service').setLevel(logging.DEBUG)
```

## Migration Guide

### From Placeholder Auth

If migrating from the placeholder authentication system:

1. **Backup Existing Data**: Export any existing user data
2. **Update Dependencies**: Install new requirements
3. **Run Database Migrations**: Initialize new user tables
4. **Update Configuration**: Set new environment variables
5. **Test Authentication**: Verify login with default admin user
6. **Migrate Users**: Create new user accounts as needed

### Database Migrations

Use Alembic for schema changes:
```bash
# Generate migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Future Enhancements

- OAuth2/OIDC integration
- LDAP/Active Directory integration
- Advanced MFA options (SMS, hardware tokens)
- Password history and complexity policies
- Advanced audit logging and SIEM integration
- API rate limiting and DDoS protection
- Certificate-based authentication