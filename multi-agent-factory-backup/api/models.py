from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, Field, validator
import re

Base = declarative_base()

# Association table for user roles (many-to-many)
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True)
)

class UserModel(Base):
    """SQLAlchemy User model for database storage."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    last_login = Column(DateTime(timezone=True))
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32))  # TOTP secret
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    roles = relationship("RoleModel", secondary=user_roles, back_populates="users")
    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")

class RoleModel(Base):
    """SQLAlchemy Role model for RBAC."""
    __tablename__ = "roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    permissions = Column(Text)  # JSON string of permissions list
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("UserModel", secondary=user_roles, back_populates="roles")

class UserSessionModel(Base):
    """SQLAlchemy model for tracking user sessions."""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    jti = Column(String(100), unique=True, nullable=False)  # JWT ID
    device_info = Column(Text)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_accessed = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    user = relationship("UserModel", back_populates="sessions")

# Pydantic models for API
class UserBase(BaseModel):
    """Base user model with common fields."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v

class UserCreate(UserBase):
    """Model for user creation."""
    password: str = Field(..., min_length=12)
    confirm_password: str
    roles: Optional[List[str]] = Field(default_factory=lambda: ["viewer"])
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserUpdate(BaseModel):
    """Model for user updates."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None

class UserResponse(UserBase):
    """Model for user responses."""
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime
    roles: List[str] = []
    
    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    """Model for password change requests."""
    current_password: str
    new_password: str = Field(..., min_length=12)
    confirm_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class LoginRequest(BaseModel):
    """Model for login requests."""
    username: str
    password: str
    mfa_token: Optional[str] = None
    remember_me: bool = False

class TokenResponse(BaseModel):
    """Model for token responses."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: UserResponse

class MFASetupResponse(BaseModel):
    """Model for MFA setup response."""
    secret: str
    qr_code_url: str
    backup_codes: List[str]

class RoleCreate(BaseModel):
    """Model for role creation."""
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    permissions: List[str] = []

class RoleUpdate(BaseModel):
    """Model for role updates."""
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None

class RoleResponse(BaseModel):
    """Model for role responses."""
    id: uuid.UUID
    name: str
    description: Optional[str]
    permissions: List[str]
    is_active: bool
    created_at: datetime
    user_count: int = 0
    
    class Config:
        from_attributes = True