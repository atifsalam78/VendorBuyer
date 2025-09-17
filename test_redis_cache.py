#!/usr/bin/env python3
"""
Test script to verify Redis cache functionality with memory fallback
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.redis_cache import RedisCache

async def test_cache():
    print("Testing Redis cache with memory fallback...")
    
    # Create cache instance
    cache = RedisCache()
    
    # Initialize Redis (should fail since Docker/Redis is not running)
    redis_connected = await cache.init_redis()
    print(f"Redis connected: {redis_connected}")
    print(f"Redis available: {cache.redis_available}")
    
    # Test set operation
    print("\n1. Testing set_likes_count...")
    post_id = "test_post_123"
    success = await cache.set_likes_count(post_id, 5)
    print(f"Set likes count for {post_id}: {success}")
    
    # Test get operation
    print("\n2. Testing get_likes_count...")
    count = await cache.get_likes_count(post_id)
    print(f"Get likes count for {post_id}: {count}")
    
    # Test increment operation
    print("\n3. Testing increment_likes_count...")
    new_count = await cache.increment_likes_count(post_id)
    print(f"Incremented likes count for {post_id}: {new_count}")
    
    # Test get after increment
    count_after = await cache.get_likes_count(post_id)
    print(f"Get likes count after increment: {count_after}")
    
    # Test decrement operation
    print("\n4. Testing decrement_likes_count...")
    new_count = await cache.decrement_likes_count(post_id)
    print(f"Decremented likes count for {post_id}: {new_count}")
    
    # Test get after decrement
    count_final = await cache.get_likes_count(post_id)
    print(f"Get likes count after decrement: {count_final}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_cache())