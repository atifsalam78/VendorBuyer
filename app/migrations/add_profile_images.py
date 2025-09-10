import asyncio
import os
from sqlalchemy import text
from app.deps import engine
from app.config import BASE_DIR

async def migrate():
    # Database path for logging purposes
    db_path = os.path.join(BASE_DIR, "bazaarhub.db")
    print(f"Starting migration: Creating profile_images table using database at {db_path}")
    
    try:
        # Start transaction
        async with engine.begin() as conn:
            # Check if the profile_images table already exists
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='profile_images'"))
            table_exists = result.fetchone() is not None
            
            if not table_exists:
                print("Creating profile_images table...")
                await conn.execute(text("""
                CREATE TABLE profile_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    profile_pic TEXT,
                    banner_pic TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
                """))
                print("profile_images table created successfully.")
            else:
                print("profile_images table already exists.")
                
                # Check if the columns exist
                result = await conn.execute(text("SELECT name FROM pragma_table_info('profile_images') WHERE name = 'profile_pic'"))
                profile_pic_exists = result.fetchone() is not None
                
                result = await conn.execute(text("SELECT name FROM pragma_table_info('profile_images') WHERE name = 'banner_pic'"))
                banner_pic_exists = result.fetchone() is not None
                
                # Add columns if they don't exist
                if not profile_pic_exists:
                    await conn.execute(text("ALTER TABLE profile_images ADD COLUMN profile_pic TEXT"))
                    print("profile_pic column added to profile_images table.")
                else:
                    print("profile_pic column already exists in profile_images table.")
                    
                if not banner_pic_exists:
                    await conn.execute(text("ALTER TABLE profile_images ADD COLUMN banner_pic TEXT"))
                    print("banner_pic column added to profile_images table.")
                else:
                    print("banner_pic column already exists in profile_images table.")
        
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate())