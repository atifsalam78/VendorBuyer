import json
from typing import Optional, Dict, Any
from .config import settings

class SimpleCache:
    def __init__(self):
        self.memory_cache: Dict[str, int] = {}
        print("Using simple in-memory cache (Redis not available)")

    async def init_redis(self) -> bool:
        """Initialize cache - always returns True for simple cache"""
        print("Simple cache initialized successfully")
        return True

    async def get_likes_count(self, post_id: int) -> Optional[int]:
        """Get likes count from cache"""
        cache_key = f"likes:{post_id}"
        return self.memory_cache.get(cache_key)

    async def set_likes_count(self, post_id: int, count: int) -> bool:
        """Set likes count in cache"""
        cache_key = f"likes:{post_id}"
        self.memory_cache[cache_key] = count
        return True

    async def increment_likes_count(self, post_id: int) -> int:
        """Increment likes count in cache"""
        cache_key = f"likes:{post_id}"
        current_count = self.memory_cache.get(cache_key, 0)
        new_count = current_count + 1
        self.memory_cache[cache_key] = new_count
        return new_count

    async def decrement_likes_count(self, post_id: int) -> int:
        """Decrement likes count in cache"""
        cache_key = f"likes:{post_id}"
        current_count = self.memory_cache.get(cache_key, 0)
        new_count = max(0, current_count - 1)  # Don't go below 0
        self.memory_cache[cache_key] = new_count
        return new_count

    async def invalidate_likes_cache(self, post_id: int) -> bool:
        """Remove likes count from cache"""
        cache_key = f"likes:{post_id}"
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        return True

    async def get_shares_count(self, post_id: int) -> Optional[int]:
        """Get shares count from cache"""
        cache_key = f"shares:{post_id}"
        return self.memory_cache.get(cache_key)

    async def set_shares_count(self, post_id: int, count: int) -> bool:
        """Set shares count in cache"""
        cache_key = f"shares:{post_id}"
        self.memory_cache[cache_key] = count
        return True

    async def increment_shares_count(self, post_id: int) -> int:
        """Increment shares count in cache"""
        cache_key = f"shares:{post_id}"
        current_count = self.memory_cache.get(cache_key, 0)
        new_count = current_count + 1
        self.memory_cache[cache_key] = new_count
        return new_count

    async def invalidate_shares_cache(self, post_id: int) -> bool:
        """Remove shares count from cache"""
        cache_key = f"shares:{post_id}"
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        return True

    async def close(self):
        """Close cache - no operation needed for memory cache"""
        pass

# Global instance
redis_cache = SimpleCache()

# FastAPI dependency
async def get_redis_cache() -> SimpleCache:
    return redis_cache