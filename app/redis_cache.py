import redis.asyncio as redis
import json
from typing import Optional, Any
import asyncio
from .config import settings

class RedisCache:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        
    async def init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            print("Redis connection established successfully")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None
    
    async def get_likes_count(self, post_id: int) -> Optional[int]:
        """Get likes count from cache"""
        if not self.redis_client:
            return None
            
        try:
            cached_count = await self.redis_client.get(f"post_likes:{post_id}")
            if cached_count is not None:
                return int(cached_count)
        except Exception:
            pass
        return None
    
    async def set_likes_count(self, post_id: int, count: int, expire: int = 3600) -> bool:
        """Set likes count in cache"""
        if not self.redis_client:
            return False
            
        try:
            await self.redis_client.setex(f"post_likes:{post_id}", expire, str(count))
            return True
        except Exception:
            return False
    
    async def increment_likes_count(self, post_id: int, amount: int = 1) -> Optional[int]:
        """Atomically increment likes count in cache"""
        if not self.redis_client:
            return None
            
        try:
            return await self.redis_client.incrby(f"post_likes:{post_id}", amount)
        except Exception:
            return None
    
    async def decrement_likes_count(self, post_id: int, amount: int = 1) -> Optional[int]:
        """Atomically decrement likes count in cache"""
        if not self.redis_client:
            return None
            
        try:
            return await self.redis_client.decrby(f"post_likes:{post_id}", amount)
        except Exception:
            return None
    
    async def invalidate_likes_cache(self, post_id: int) -> bool:
        """Remove likes count from cache"""
        if not self.redis_client:
            return False
            
        try:
            await self.redis_client.delete(f"post_likes:{post_id}")
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

# Global Redis cache instance
redis_cache = RedisCache()

async def get_redis_cache() -> RedisCache:
    """Dependency for FastAPI to get Redis cache"""
    if redis_cache.redis_client is None:
        await redis_cache.init_redis()
    return redis_cache