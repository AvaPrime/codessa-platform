"""
Redis-based caching layer for fast temporary storage
"""
import os
import redis
import json
from typing import Any, Optional

class CacheStore:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.client = redis.Redis(
            host=self.redis_host, 
            port=self.redis_port, 
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            print(f"❌ Cache get failed for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self.client.setex(key, ttl, value)
        except Exception as e:
            print(f"❌ Cache set failed for {key}: {e}")
    
    def delete(self, key: str):
        """Delete key from cache"""
        try:
            self.client.delete(key)
        except Exception as e:
            print(f"❌ Cache delete failed for {key}: {e}")
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"❌ Cache exists check failed for {key}: {e}")
            return False

# Global instance  
cache = CacheStore()
