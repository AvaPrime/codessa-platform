from __future__ import annotations

import os
import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import wraps

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis.asyncio as redis
from sqlalchemy.orm import Session

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Redis client for token blacklisting
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Redis connection function
async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

security = HTTPBearer()

class TokenData(BaseModel):
    user_id: str
    username: str
    roles: List[str]
    scopes: List[str]
    exp: int
    iat: int
    jti: str  # JWT ID for blacklisting

class User(BaseModel):
    user_id: str
    username: str
    roles: List[str]
    scopes: List[str]

# Role-based permissions
ROLE_PERMISSIONS = {
    "admin": [
        "tasks:create", "tasks:read", "tasks:delete",
        "results:read", "results:delete",
        "ingest:create", "ingest:read",
        "system:health", "system:metrics"
    ],
    "operator": [
        "tasks:create", "tasks:read",
        "results:read",
        "ingest:create",
        "system:health"
    ],
    "viewer": [
        "tasks:read",
        "results:read",
        "system:health"
    ],
    "agent": [
        "tasks:read",  # Agents can read their assigned tasks
        "results:create",  # Agents can submit results
        "system:health"
    ],
    "agent-research": [
        "tasks:read", "results:create", "system:health"
    ],
    "agent-analysis": [
        "tasks:read", "results:create", "system:health"
    ],
    "agent-synthesis": [
        "tasks:read", "results:create", "system:health"
    ],
    "agent-validation": [
        "tasks:read", "results:create", "system:health"
    ],
    "agent-coordination": [
        "tasks:read", "results:create", "system:health"
    ]
}

def create_access_token(user_id: str, username: str, roles: List[str]) -> str:
    """Create a JWT access token with user claims and permissions."""
    
    # Aggregate permissions from all roles
    scopes = set()
    for role in roles:
        scopes.update(ROLE_PERMISSIONS.get(role, []))
    
    now = datetime.utcnow()
    exp = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    jti = f"{user_id}_{int(time.time())}"
    
    payload = {
        "user_id": user_id,
        "username": username,
        "roles": roles,
        "scopes": list(scopes),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": jti
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Verify JWT token and return token data."""
    
    try:
        # Decode JWT
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        token_data = TokenData(**payload)
        
        # Check if token is blacklisted
        is_blacklisted = await r.get(f"blacklist:{token_data.jti}")
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return token_data
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user(token_data: TokenData = Depends(verify_token)) -> User:
    """Get current user from token data."""
    return User(
        user_id=token_data.user_id,
        username=token_data.username,
        roles=token_data.roles,
        scopes=token_data.scopes
    )

# Additional permission scopes for user management
USER_MANAGEMENT_PERMISSIONS = {
    "admin": [
        "users:read", "users:write", "users:delete",
        "admin:read", "admin:write", "admin:delete"
    ],
    "operator": [
        "users:read"
    ]
}

# Update role permissions to include user management
for role, perms in USER_MANAGEMENT_PERMISSIONS.items():
    if role in ROLE_PERMISSIONS:
        ROLE_PERMISSIONS[role].extend(perms)

def require_scope(required_scope: str):
    """Decorator to require specific scope for endpoint access."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (injected by FastAPI dependency)
            user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    user = value
                    break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if required_scope not in user.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required scope: {required_scope}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def blacklist_token(jti: str, exp: int):
    """Add token to blacklist until expiration."""
    ttl = exp - int(time.time())
    if ttl > 0:
        await r.setex(f"blacklist:{jti}", ttl, "1")

# NATS Subject Security
def generate_nats_hmac(subject: str, payload: bytes, secret: str) -> str:
    """Generate HMAC signature for NATS message authentication."""
    import hmac
    import hashlib
    import base64
    
    message = f"{subject}:{payload.decode('utf-8')}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    return base64.b64encode(signature).decode('utf-8')

def verify_nats_hmac(subject: str, payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature for NATS message."""
    expected_signature = generate_nats_hmac(subject, payload, secret)
    return hmac.compare_digest(signature, expected_signature)

# Task Envelope Signing
class SignedTaskEnvelope(BaseModel):
    task_id: str
    role: str
    payload: Dict[str, Any]
    timestamp: int
    signature: str
    
def sign_task_envelope(task: Dict[str, Any], secret: str) -> SignedTaskEnvelope:
    """Sign a task envelope for integrity verification."""
    import hmac
    import hashlib
    import json
    
    timestamp = int(time.time())
    
    # Create canonical representation
    canonical_task = {
        "task_id": task["task_id"],
        "role": task["role"],
        "payload": task["payload"],
        "timestamp": timestamp
    }
    
    # Generate signature
    message = json.dumps(canonical_task, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return SignedTaskEnvelope(
        task_id=task["task_id"],
        role=task["role"],
        payload=task["payload"],
        timestamp=timestamp,
        signature=signature
    )

def verify_task_envelope(envelope: SignedTaskEnvelope, secret: str, max_age_seconds: int = 300) -> bool:
    """Verify signed task envelope integrity and freshness."""
    import hmac
    import hashlib
    import json
    
    # Check timestamp freshness
    current_time = int(time.time())
    if current_time - envelope.timestamp > max_age_seconds:
        return False
    
    # Recreate canonical representation
    canonical_task = {
        "task_id": envelope.task_id,
        "role": envelope.role,
        "payload": envelope.payload,
        "timestamp": envelope.timestamp
    }
    
    # Verify signature
    message = json.dumps(canonical_task, sort_keys=True, separators=(',', ':'))
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(envelope.signature, expected_signature)

# Enhanced JWT security configuration
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis.asyncio as redis

# Security hardening configurations
JWT_ALGORITHM = "RS256"  # Use RSA instead of HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Shorter token lifetime
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30
PASSWORD_MIN_LENGTH = 12
PASSWORD_REQUIRE_SPECIAL = True

# Enhanced password hashing
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64MB
    argon2__time_cost=3,
    argon2__parallelism=1,
)

class SecurityHardenedAuth:
    def __init__(self):
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self.failed_attempts_prefix = "failed_attempts:"
        self.blacklist_prefix = "token_blacklist:"
    
    async def validate_password_strength(self, password: str) -> bool:
        """Enforce strong password policy"""
        if len(password) < PASSWORD_MIN_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
            )
        
        if not any(c.isupper() for c in password):
            raise HTTPException(status_code=400, detail="Password must contain uppercase letter")
        
        if not any(c.islower() for c in password):
            raise HTTPException(status_code=400, detail="Password must contain lowercase letter")
        
        if not any(c.isdigit() for c in password):
            raise HTTPException(status_code=400, detail="Password must contain digit")
        
        if PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            raise HTTPException(status_code=400, detail="Password must contain special character")
        
        return True
    
    async def check_rate_limiting(self, identifier: str) -> bool:
        """Check if user/IP is rate limited"""
        key = f"{self.failed_attempts_prefix}{identifier}"
        attempts = await self.redis_client.get(key)
        
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
            ttl = await self.redis_client.ttl(key)
            if ttl > 0:
                raise HTTPException(
                    status_code=429,
                    detail=f"Account locked. Try again in {ttl // 60} minutes"
                )
        
        return True
    
    async def record_failed_attempt(self, identifier: str):
        """Record failed login attempt"""
        key = f"{self.failed_attempts_prefix}{identifier}"
        await self.redis_client.incr(key)
        await self.redis_client.expire(key, LOCKOUT_DURATION_MINUTES * 60)
    
    async def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts on successful login"""
        key = f"{self.failed_attempts_prefix}{identifier}"
        await self.redis_client.delete(key)
    
    async def blacklist_token(self, token: str):
        """Add token to blacklist"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload.get("exp")
            if exp:
                ttl = exp - datetime.utcnow().timestamp()
                if ttl > 0:
                    key = f"{self.blacklist_prefix}{token}"
                    await self.redis_client.setex(key, int(ttl), "blacklisted")
        except JWTError:
            pass
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        key = f"{self.blacklist_prefix}{token}"
        return await self.redis_client.exists(key)

# Multi-factor authentication support
class MFAManager:
    def __init__(self):
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    
    async def generate_totp_secret(self, user_id: str) -> str:
        """Generate TOTP secret for user"""
        import pyotp
        secret = pyotp.random_base32()
        await self.redis_client.setex(f"totp_secret:{user_id}", 3600, secret)
        return secret
    
    async def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        import pyotp
        secret = await self.redis_client.get(f"totp_secret:{user_id}")
        if not secret:
            return False
        
        totp = pyotp.TOTP(secret.decode())
        return totp.verify(token, valid_window=1)