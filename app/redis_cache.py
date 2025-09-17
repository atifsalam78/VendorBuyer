import redis.asyncio as redis
import json
from typing import Optional, Any, Dict
import asyncio
from .config import settings

class RedisCache:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[int, int] = {}  # In-memory fallback cache
        self.redis_available: bool = False
        
    async def init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,  # 2 second timeout
                socket_timeout=2,
                retry_on_timeout=True,
                max_connections=10
            )
            # Test connection
            await self.redis_client.ping()
            print("Redis connection established successfully")
            self.redis_available = True
            return True
        except Exception as e:
            print(f"Redis connection failed: {e}")
            print("Warning: Redis is not available. Using in-memory cache fallback.")
            self.redis_client = None
            self.redis_available = False
            return False
    
    async def get_likes_count(self, post_id: int) -> Optional[int]:
        """Get likes count from cache"""
        if not self.redis_available:
            # Use in-memory cache fallback
            return self.memory_cache.get(post_id)
            
        try:
            key = f"post_likes:{post_id}"
            result = await self.redis_client.get(key)
            if result is None:
                print(f"Cache miss for post {post_id}")
                return None
            print(f"Cache hit for post {post_id}: {result}")
            return int(result)
        except Exception as e:
            print(f"Error getting likes count for post {post_id}: {e}")
            # Fallback to in-memory cache
            return self.memory_cache.get(post_id)
    
    async def set_likes_count(self, post_id: int, count: int, expire: int = 3600) -> bool:
        """Set likes count in cache"""
        # Always update in-memory cache
        self.memory_cache[post_id] = count
        
        if not self.redis_available:
            return True
            
        try:
            await self.redis_client.setex(f"post_likes:{post_id}", expire, str(count))
            return True
        except Exception:
            return False
    
    async def increment_likes_count(self, post_id: int, amount: int = 1) -> Optional[int]:
        """Atomically increment likes count in cache"""
        # Update in-memory cache
        current = self.memory_cache.get(post_id, 0)
        new_count = current + amount
        self.memory_cache[post_id] = new_count
        
        if not self.redis_available:
            return new_count
            
        try:
            # Check if key exists first, if not initialize it
            key = f"post_likes:{post_id}"
            exists = await self.redis_client.exists(key)
            if not exists:
                # Initialize with 0 first
                await self.redis_client.set(key, "0")
            return await self.redis_client.incrby(key, amount)
        except Exception:
            return new_count
    
    async def decrement_likes_count(self, post_id: int, amount: int = 1) -> Optional[int]:
        """Atomically decrement likes count in cache"""
        # Update in-memory cache
        current = self.memory_cache.get(post_id, 0)
        new_count = max(0, current - amount)  # Don't go below 0
        self.memory_cache[post_id] = new_count
        
        if not self.redis_available:
            return new_count
            
        try:
            # Check if key exists first, if not initialize it
            key = f"post_likes:{post_id}"
            exists = await self.redis_client.exists(key)
            if not exists:
                # Initialize with 0 first
                await self.redis_client.set(key, "0")
            return await self.redis_client.decrby(key, amount)
        except Exception:
            return new_count
    
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