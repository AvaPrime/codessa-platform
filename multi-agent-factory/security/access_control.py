# Enhanced access control with principle of least privilege
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from enum import Enum
import aioredis
from cryptography.fernet import Fernet

class AccessLevel(Enum):
    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3
    SUPER_ADMIN = 4

@dataclass
class AccessPolicy:
    resource: str
    level: AccessLevel
    conditions: Dict[str, any]
    time_restrictions: Optional[Dict[str, str]] = None
    ip_restrictions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None

class EnhancedAccessControl:
    def __init__(self):
        self.redis = None
        self.policies_cache = {}
        self.access_matrix = self._build_access_matrix()
    
    async def initialize(self):
        """Initialize access control system"""
        self.redis = aioredis.from_url("redis://redis:6379")
        await self._load_policies()
    
    def _build_access_matrix(self) -> Dict[str, Dict[str, AccessLevel]]:
        """Build role-based access control matrix"""
        return {
            "super_admin": {
                "system:*": AccessLevel.SUPER_ADMIN,
                "data:*": AccessLevel.SUPER_ADMIN,
                "users:*": AccessLevel.SUPER_ADMIN,
                "security:*": AccessLevel.SUPER_ADMIN
            },
            "admin": {
                "system:config": AccessLevel.ADMIN,
                "system:monitor": AccessLevel.READ,
                "data:export": AccessLevel.WRITE,
                "users:manage": AccessLevel.WRITE,
                "agents:*": AccessLevel.ADMIN
            },
            "operator": {
                "system:monitor": AccessLevel.READ,
                "tasks:*": AccessLevel.WRITE,
                "agents:view": AccessLevel.READ,
                "data:read": AccessLevel.READ
            },
            "user": {
                "tasks:own": AccessLevel.WRITE,
                "tasks:read": AccessLevel.READ,
                "profile:own": AccessLevel.WRITE
            },
            "agent": {
                "tasks:assigned": AccessLevel.READ,
                "results:create": AccessLevel.WRITE,
                "system:health": AccessLevel.READ
            },
            "readonly": {
                "tasks:read": AccessLevel.READ,
                "system:health": AccessLevel.READ
            }
        }
    
    async def check_access(self, user_id: str, resource: str, 
                          action: str, context: Dict[str, any] = None) -> bool:
        """Check if user has access to resource/action"""
        try:
            # Get user roles and permissions
            user_roles = await self._get_user_roles(user_id)
            
            # Check each role for access
            for role in user_roles:
                if await self._check_role_access(role, resource, action, context):
                    # Log successful access
                    await self._log_access_attempt(user_id, resource, action, True, context)
                    return True
            
            # Log failed access attempt
            await self._log_access_attempt(user_id, resource, action, False, context)
            return False
            
        except Exception as e:
            # Log error and deny access
            await self._log_access_error(user_id, resource, action, str(e))
            return False
    
    async def _check_role_access(self, role: str, resource: str, 
                               action: str, context: Dict[str, any]) -> bool:
        """Check if role has access to resource/action"""
        role_permissions = self.access_matrix.get(role, {})
        
        # Check exact match
        if resource in role_permissions:
            required_level = self._get_required_access_level(action)
            return role_permissions[resource].value >= required_level.value
        
        # Check wildcard matches
        for permission, level in role_permissions.items():
            if permission.endswith(":*"):
                prefix = permission[:-2]
                if resource.startswith(prefix):
                    required_level = self._get_required_access_level(action)
                    return level.value >= required_level.value
        
        return False
    
    def _get_required_access_level(self, action: str) -> AccessLevel:
        """Get required access level for action"""
        action_levels = {
            "read": AccessLevel.READ,
            "list": AccessLevel.READ,
            "view": AccessLevel.READ,
            "create": AccessLevel.WRITE,
            "update": AccessLevel.WRITE,
            "delete": AccessLevel.WRITE,
            "manage": AccessLevel.ADMIN,
            "configure": AccessLevel.ADMIN,
            "admin": AccessLevel.SUPER_ADMIN
        }
        return action_levels.get(action, AccessLevel.WRITE)
    
    async def _get_user_roles(self, user_id: str) -> List[str]:
        """Get user roles from cache/database"""
        cache_key = f"user_roles:{user_id}"
        cached_roles = await self.redis.get(cache_key)
        
        if cached_roles:
            return json.loads(cached_roles)
        
        # Fetch from database (implement based on your user system)
        roles = await self._fetch_user_roles_from_db(user_id)
        
        # Cache for 5 minutes
        await self.redis.setex(cache_key, 300, json.dumps(roles))
        return roles
    
    async def _log_access_attempt(self, user_id: str, resource: str, 
                                action: str, success: bool, context: Dict[str, any]):
        """Log access attempt for auditing"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "success": success,
            "ip_address": context.get("ip_address") if context else None,
            "user_agent": context.get("user_agent") if context else None
        }
        
        # Store in Redis for real-time monitoring
        await self.redis.lpush("access_logs", json.dumps(log_entry))
        await self.redis.ltrim("access_logs", 0, 10000)  # Keep last 10k entries