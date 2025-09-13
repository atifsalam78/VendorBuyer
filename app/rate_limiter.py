from typing import Optional
import time
from .config import settings
from .redis_cache import get_redis_cache

class RateLimiter:
    def __init__(self):
        pass
    
    async def check_rate_limit(self, user_id: int, action: str) -> bool:
        """Check if user has exceeded rate limits for an action"""
        redis_cache = await get_redis_cache()
        
        if not redis_cache.redis_client:
            return True  # Allow if Redis is not available
        
        current_time = int(time.time())
        
        # Check minute-based rate limit
        minute_key = f"rate_limit:{action}:{user_id}:minute"
        minute_count = await redis_cache.redis_client.get(minute_key)
        
        if minute_count and int(minute_count) >= settings.RATE_LIMIT_LIKES_PER_MINUTE:
            return False
        
        # Check hour-based rate limit
        hour_key = f"rate_limit:{action}:{user_id}:hour"
        hour_count = await redis_cache.redis_client.get(hour_key)
        
        if hour_count and int(hour_count) >= settings.RATE_LIMIT_LIKES_PER_HOUR:
            return False
        
        return True
    
    async def increment_rate_limit(self, user_id: int, action: str) -> None:
        """Increment rate limit counters for a user action"""
        redis_cache = await get_redis_cache()
        
        if not redis_cache.redis_client:
            return
        
        current_time = int(time.time())
        
        # Minute-based rate limit
        minute_key = f"rate_limit:{action}:{user_id}:minute"
        await redis_cache.redis_client.multi_exec()
        await redis_cache.redis_client.incr(minute_key)
        await redis_cache.redis_client.expire(minute_key, 60)  # Expire after 60 seconds
        
        # Hour-based rate limit
        hour_key = f"rate_limit:{action}:{user_id}:hour"
        await redis_cache.redis_client.multi_exec()
        await redis_cache.redis_client.incr(hour_key)
        await redis_cache.redis_client.expire(hour_key, 3600)  # Expire after 1 hour

# Global rate limiter instance
rate_limiter = RateLimiter()

async def get_rate_limiter() -> RateLimiter:
    """Dependency for FastAPI to get rate limiter"""
    return rate_limiter