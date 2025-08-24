# Comprehensive RBAC implementation
from enum import Enum
from typing import List, Dict, Set
from dataclasses import dataclass
from functools import wraps
from fastapi import HTTPException, Depends

class Permission(Enum):
    # Task permissions
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    
    # Agent permissions
    AGENT_MANAGE = "agent:manage"
    AGENT_VIEW = "agent:view"
    AGENT_DEPLOY = "agent:deploy"
    
    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_CONFIG = "system:config"
    
    # Data permissions
    DATA_EXPORT = "data:export"
    DATA_DELETE = "data:delete"
    DATA_BACKUP = "data:backup"
    
    # Security permissions
    SECURITY_AUDIT = "security:audit"
    SECURITY_MANAGE = "security:manage"

@dataclass
class Role:
    name: str
    permissions: Set[Permission]
    description: str
    max_session_duration: int = 3600  # seconds

# Define security-hardened roles
ROLES = {
    "super_admin": Role(
        name="super_admin",
        permissions=set(Permission),  # All permissions
        description="Super administrator with full system access",
        max_session_duration=1800  # 30 minutes
    ),
    "admin": Role(
        name="admin",
        permissions={
            Permission.TASK_CREATE, Permission.TASK_READ, Permission.TASK_UPDATE,
            Permission.AGENT_MANAGE, Permission.AGENT_VIEW, Permission.AGENT_DEPLOY,
            Permission.SYSTEM_MONITOR, Permission.SYSTEM_CONFIG,
            Permission.DATA_EXPORT, Permission.DATA_BACKUP
        },
        description="System administrator",
        max_session_duration=3600  # 1 hour
    ),
    "operator": Role(
        name="operator",
        permissions={
            Permission.TASK_CREATE, Permission.TASK_READ, Permission.TASK_UPDATE,
            Permission.AGENT_VIEW, Permission.SYSTEM_MONITOR
        },
        description="System operator",
        max_session_duration=7200  # 2 hours
    ),
    "user": Role(
        name="user",
        permissions={
            Permission.TASK_CREATE, Permission.TASK_READ
        },
        description="Regular user",
        max_session_duration=14400  # 4 hours
    ),
    "readonly": Role(
        name="readonly",
        permissions={
            Permission.TASK_READ, Permission.AGENT_VIEW, Permission.SYSTEM_MONITOR
        },
        description="Read-only access",
        max_session_duration=28800  # 8 hours
    )
}

class RBACManager:
    def __init__(self):
        self.roles = ROLES
    
    def has_permission(self, user_roles: List[str], required_permission: Permission) -> bool:
        """Check if user has required permission"""
        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role and required_permission in role.permissions:
                return True
        return False
    
    def get_user_permissions(self, user_roles: List[str]) -> Set[Permission]:
        """Get all permissions for user roles"""
        permissions = set()
        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role:
                permissions.update(role.permissions)
        return permissions

# Permission decorator
def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from request context
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            rbac = RBACManager()
            if not rbac.has_permission(user.roles, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission {permission.value} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator