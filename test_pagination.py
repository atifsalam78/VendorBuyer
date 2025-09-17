#!/usr/bin/env python3
"""
Test script to verify pagination is working correctly with the actual database
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from sqlalchemy.future import select
from sqlalchemy import func
from deps import get_db
from models import Post

async def test_pagination():
    print("Testing pagination with actual database...")
    
    async for db in get_db():
        # Count total posts
        total_result = await db.execute(select(func.count()).select_from(Post))
        total_posts = total_result.scalar()
        
        # Count public posts
        public_result = await db.execute(
            select(func.count()).select_from(Post)
            .where(Post.visibility == "public")
        )
        public_posts = public_result.scalar()
        
        print(f"Total posts in database: {total_posts}")
        print(f"Public posts: {public_posts}")
        print(f"Non-public posts: {total_posts - public_posts}")
        
        # Test pagination query
        posts_per_page = 10
        page = 1
        offset = (page - 1) * posts_per_page
        
        # Fetch paginated public posts
        result = await db.execute(
            select(Post)
            .where(Post.visibility == "public")
            .order_by(Post.created_at.desc())
            .limit(posts_per_page)
            .offset(offset)
        )
        
        posts = result.scalars().all()
        print(f"Page {page}: {len(posts)} posts")
        
        # Calculate total pages
        total_pages = (public_posts + posts_per_page - 1) // posts_per_page
        print(f"Total pages needed: {total_pages}")
        print(f"Posts per page: {posts_per_page}")

if __name__ == "__main__":
    asyncio.run(test_pagination())