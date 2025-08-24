from __future__ import annotations

import json
import secrets
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from passlib.context import CryptContext
from fastapi import HTTPException, status
import redis.asyncio as redis

from .models import (
    UserModel, RoleModel, UserSessionModel,
    UserCreate, UserUpdate, PasswordChange,
    LoginRequest, UserResponse, RoleResponse
)
from .auth import create_access_token, ROLE_PERMISSIONS

# Password hashing configuration
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64MB
    argon2__time_cost=3,
    argon2__parallelism=1,
)

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30
SESSION_CLEANUP_INTERVAL = 3600  # 1 hour

class UserService:
    """Service class for user management operations."""
    
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
    
    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    async def is_user_locked(self, user: UserModel) -> bool:
        """Check if user account is locked due to failed login attempts."""
        if user.locked_until and user.locked_until > datetime.utcnow():
            return True
        return False
    
    async def record_failed_login(self, user: UserModel) -> None:
        """Record a failed login attempt and lock account if necessary."""
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        
        self.db.commit()
    
    async def clear_failed_attempts(self, user: UserModel) -> None:
        """Clear failed login attempts after successful login."""
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self.db.commit()
    
    async def create_user(self, user_data: UserCreate, created_by: Optional[str] = None) -> UserResponse:
        """Create a new user account."""
        # Check if username or email already exists
        existing_user = self.db.query(UserModel).filter(
            or_(UserModel.username == user_data.username, UserModel.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create user
        hashed_password = self.hash_password(user_data.password)
        db_user = UserModel(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_verified=True  # Auto-verify for now, can be changed for email verification
        )
        
        # Assign roles
        for role_name in user_data.roles:
            role = self.db.query(RoleModel).filter(RoleModel.name == role_name).first()
            if role:
                db_user.roles.append(role)
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        # Log user creation
        await self.redis.lpush(
            "audit:user_created",
            json.dumps({
                "user_id": str(db_user.id),
                "username": db_user.username,
                "created_by": created_by,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return self._user_to_response(db_user)
    
    async def authenticate_user(self, login_data: LoginRequest, ip_address: str, user_agent: str) -> Tuple[UserResponse, str]:
        """Authenticate user and return user data with access token."""
        # Get user by username or email
        user = self.db.query(UserModel).filter(
            or_(UserModel.username == login_data.username, UserModel.email == login_data.username)
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if account is locked
        if await self.is_user_locked(user):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked due to too many failed attempts. Try again after {LOCKOUT_DURATION_MINUTES} minutes."
            )
        
        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Verify password
        if not self.verify_password(login_data.password, user.hashed_password):
            await self.record_failed_login(user)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check MFA if enabled
        if user.mfa_enabled:
            if not login_data.mfa_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MFA token required"
                )
            
            if not self.verify_mfa_token(user, login_data.mfa_token):
                await self.record_failed_login(user)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA token"
                )
        
        # Clear failed attempts and update last login
        await self.clear_failed_attempts(user)
        
        # Create access token
        role_names = [role.name for role in user.roles]
        token = create_access_token(str(user.id), user.username, role_names)
        
        # Create session record
        session = UserSessionModel(
            user_id=user.id,
            jti=f"{user.id}_{int(datetime.utcnow().timestamp())}",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        self.db.add(session)
        self.db.commit()
        
        # Log successful login
        await self.redis.lpush(
            "audit:user_login",
            json.dumps({
                "user_id": str(user.id),
                "username": user.username,
                "ip_address": ip_address,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return self._user_to_response(user), token
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            return self._user_to_response(user)
        return None
    
    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """Get user by username."""
        user = self.db.query(UserModel).filter(UserModel.username == username).first()
        if user:
            return self._user_to_response(user)
        return None
    
    async def update_user(self, user_id: str, user_data: UserUpdate, updated_by: str) -> UserResponse:
        """Update user information."""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        if user_data.email is not None:
            # Check if email is already taken
            existing = self.db.query(UserModel).filter(
                and_(UserModel.email == user_data.email, UserModel.id != user_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            user.email = user_data.email
        
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        
        if user_data.roles is not None:
            # Clear existing roles and add new ones
            user.roles.clear()
            for role_name in user_data.roles:
                role = self.db.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role:
                    user.roles.append(role)
        
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        # Log user update
        await self.redis.lpush(
            "audit:user_updated",
            json.dumps({
                "user_id": str(user.id),
                "username": user.username,
                "updated_by": updated_by,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return self._user_to_response(user)
    
    async def change_password(self, user_id: str, password_data: PasswordChange) -> None:
        """Change user password."""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not self.verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.hashed_password = self.hash_password(password_data.new_password)
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Invalidate all user sessions
        await self.invalidate_user_sessions(user_id)
        
        # Log password change
        await self.redis.lpush(
            "audit:password_changed",
            json.dumps({
                "user_id": str(user.id),
                "username": user.username,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
    
    async def setup_mfa(self, user_id: str) -> dict:
        """Setup MFA for user."""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        
        # Generate QR code
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="Multi-Agent Factory"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()
        
        # Generate backup codes
        backup_codes = [secrets.token_hex(8) for _ in range(10)]
        
        self.db.commit()
        
        return {
            "secret": secret,
            "qr_code_url": f"data:image/png;base64,{qr_code_data}",
            "backup_codes": backup_codes
        }
    
    def verify_mfa_token(self, user: UserModel, token: str) -> bool:
        """Verify MFA token."""
        if not user.mfa_secret:
            return False
        
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(token, valid_window=1)
    
    async def enable_mfa(self, user_id: str, token: str) -> None:
        """Enable MFA after verifying setup token."""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not self.verify_mfa_token(user, token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA token"
            )
        
        user.mfa_enabled = True
        self.db.commit()
    
    async def disable_mfa(self, user_id: str) -> None:
        """Disable MFA for user."""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.mfa_enabled = False
        user.mfa_secret = None
        self.db.commit()
    
    async def invalidate_user_sessions(self, user_id: str) -> None:
        """Invalidate all sessions for a user."""
        sessions = self.db.query(UserSessionModel).filter(
            UserSessionModel.user_id == user_id,
            UserSessionModel.is_active == True
        ).all()
        
        for session in sessions:
            session.is_active = False
            # Add to Redis blacklist
            await self.redis.set(
                f"blacklist:{session.jti}",
                "revoked",
                ex=int((session.expires_at - datetime.utcnow()).total_seconds())
            )
        
        self.db.commit()
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """List all users with pagination."""
        users = self.db.query(UserModel).offset(skip).limit(limit).all()
        return [self._user_to_response(user) for user in users]
    
    async def delete_user(self, user_id: str, deleted_by: str) -> None:
        """Soft delete a user (deactivate)."""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Invalidate all user sessions
        await self.invalidate_user_sessions(user_id)
        
        # Log user deletion
        await self.redis.lpush(
            "audit:user_deleted",
            json.dumps({
                "user_id": str(user.id),
                "username": user.username,
                "deleted_by": deleted_by,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
    
    def _user_to_response(self, user: UserModel) -> UserResponse:
        """Convert UserModel to UserResponse."""
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
            last_login=user.last_login,
            created_at=user.created_at,
            roles=[role.name for role in user.roles]
        )

class RoleService:
    """Service class for role management operations."""
    
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
    
    async def create_role(self, name: str, description: str, permissions: List[str]) -> RoleResponse:
        """Create a new role."""
        # Check if role already exists
        existing_role = self.db.query(RoleModel).filter(RoleModel.name == name).first()
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role already exists"
            )
        
        # Validate permissions
        all_permissions = set()
        for role_perms in ROLE_PERMISSIONS.values():
            all_permissions.update(role_perms)
        
        invalid_perms = set(permissions) - all_permissions
        if invalid_perms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permissions: {', '.join(invalid_perms)}"
            )
        
        # Create role
        role = RoleModel(
            name=name,
            description=description,
            permissions=json.dumps(permissions)
        )
        
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        
        return self._role_to_response(role)
    
    async def get_role(self, role_id: str) -> Optional[RoleResponse]:
        """Get role by ID."""
        role = self.db.query(RoleModel).filter(RoleModel.id == role_id).first()
        if role:
            return self._role_to_response(role)
        return None
    
    async def list_roles(self) -> List[RoleResponse]:
        """List all roles."""
        roles = self.db.query(RoleModel).filter(RoleModel.is_active == True).all()
        return [self._role_to_response(role) for role in roles]
    
    async def update_role(self, role_id: str, description: str = None, permissions: List[str] = None) -> RoleResponse:
        """Update role."""
        role = self.db.query(RoleModel).filter(RoleModel.id == role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        if description is not None:
            role.description = description
        
        if permissions is not None:
            # Validate permissions
            all_permissions = set()
            for role_perms in ROLE_PERMISSIONS.values():
                all_permissions.update(role_perms)
            
            invalid_perms = set(permissions) - all_permissions
            if invalid_perms:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid permissions: {', '.join(invalid_perms)}"
                )
            
            role.permissions = json.dumps(permissions)
        
        role.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(role)
        
        return self._role_to_response(role)
    
    async def delete_role(self, role_id: str) -> None:
        """Soft delete a role."""
        role = self.db.query(RoleModel).filter(RoleModel.id == role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Check if role is in use
        user_count = len(role.users)
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete role: {user_count} users are assigned to this role"
            )
        
        role.is_active = False
        role.updated_at = datetime.utcnow()
        self.db.commit()
    
    def _role_to_response(self, role: RoleModel) -> RoleResponse:
        """Convert RoleModel to RoleResponse."""
        permissions = json.loads(role.permissions) if role.permissions else []
        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            is_active=role.is_active,
            created_at=role.created_at,
            user_count=len(role.users)
        )