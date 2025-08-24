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
        """Check if key exists in cache"""
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"❌ Cache exists check failed for {key}: {e}")
            return False
    
    def get_memory_usage(self) -> dict:
        """Get Redis memory usage statistics"""
        try:
            info = self.client.info('memory')
            return {
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'used_memory_peak_human': info.get('used_memory_peak_human', '0B'),
                'maxmemory': info.get('maxmemory', 0),
                'maxmemory_human': info.get('maxmemory_human', 'unlimited')
            }
        except Exception as e:
            print(f"❌ Memory usage check failed: {e}")
            return {}
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern. Returns number of keys deleted."""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"❌ Pattern clear failed for {pattern}: {e}")
            return 0

# Global cache instance
cache = CacheStore()
