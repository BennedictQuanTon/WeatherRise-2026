import os
import json
import hashlib
from typing import Any, Optional
import redis.asyncio as redis

class CacheClient:
    """
    Shared Redis cache client for the Intelligence Layer.
    Uses REDIS_URL environment variable.
    """
    def __init__(self, redis_url: Optional[str] = None):
        self.redis = redis.from_url("redis://weatherise-redis:6379", decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"[CacheClient] Failed to get key {key}: {e}")
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 900) -> bool:
        try:
            await self.redis.setex(key, ttl_seconds, json.dumps(value))
            return True
        except Exception as e:
            print(f"[CacheClient] Failed to set key {key}: {e}")
            return False

    @staticmethod
    def generate_key(*args) -> str:
        """Generate a SHA256 cache key from string arguments."""
        key_string = ",".join(str(a) for a in args)
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()

_cache_client_instance = None

def get_cache_client() -> CacheClient:
    global _cache_client_instance
    if _cache_client_instance is None:
        _cache_client_instance = CacheClient()
    return _cache_client_instance
