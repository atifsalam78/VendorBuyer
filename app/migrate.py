import asyncio
import os
from sqlalchemy import text
from app.deps import engine
from app.config import BASE_DIR

async def migrate():
    # Database path for logging purposes
    db_path = os.path.join(BASE_DIR, "bazaarhub.db")
    print(f"Starting migrations using database at {db_path}")
    
    try:
        # Start transaction
        async with engine.begin() as conn:
            # PART 1: Create profile_images table
            print("\nMigration 1: Adding profile_images table...")
            
            # Check if profile_images table exists
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='profile_images'"))
            table_exists = result.fetchone() is not None
            
            if not table_exists:
                print("Creating profile_images table...")
                await conn.execute(text("""
                CREATE TABLE profile_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    profile_pic TEXT,
                    banner_pic TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                
                if not banner_pic_exists:
                    await conn.execute(text("ALTER TABLE profile_images ADD COLUMN banner_pic TEXT"))
                    print("banner_pic column added to profile_images table.")
            
            # PART 2: Update profiles table
            print("\nMigration 2: Adding new fields to profiles table...")
            
            # Check if the columns already exist
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'connections_count'"))
            connections_count_exists = result.fetchone() is not None
            
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'followers_count'"))
            followers_count_exists = result.fetchone() is not None
            
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'following_count'"))
            following_count_exists = result.fetchone() is not None
            
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'tagline'"))
            tagline_exists = result.fetchone() is not None
            
            # Check if social media fields exist
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'linkedin'"))
            linkedin_exists = result.fetchone() is not None
            
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'twitter'"))
            twitter_exists = result.fetchone() is not None
            
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'facebook'"))
            facebook_exists = result.fetchone() is not None
            
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'instagram'"))
            instagram_exists = result.fetchone() is not None
            
            # Add columns if they don't exist
            if not connections_count_exists:
                await conn.execute(text("ALTER TABLE profiles ADD COLUMN connections_count INTEGER DEFAULT 0"))
                print("connections_count column added to profiles table.")
            else:
                print("connections_count column already exists in profiles table.")
                
            if not followers_count_exists:
                await conn.execute(text("ALTER TABLE profiles ADD COLUMN followers_count INTEGER DEFAULT 0"))
                print("followers_count column added to profiles table.")
            else:
                print("followers_count column already exists in profiles table.")
                
            if not following_count_exists:
                await conn.execute(text("ALTER TABLE profiles ADD COLUMN following_count INTEGER DEFAULT 0"))
                print("following_count column added to profiles table.")
            else:
                print("following_count column already exists in profiles table.")
                
            if not tagline_exists:
                await conn.execute(text("ALTER TABLE profiles ADD COLUMN tagline VARCHAR"))
                print("tagline column added to profiles table.")
            else:
                print("tagline column already exists in profiles table.")
                
            # Add social media columns if they don't exist
            if not linkedin_exists:
                await conn.execute(text("ALTER TABLE profiles ADD COLUMN linkedin VARCHAR"))
                print("linkedin column added to profiles table.")
            else:
                print("linkedin column already exists in profiles table.")
                
            if not twitter_exists:
                await conn.execute(text("ALTER TABLE profiles ADD COLUMN twitter VARCHAR"))
                print("twitter column added to profiles table.")
            else:
                print("twitter column already exists in profiles table.")
                
            if not facebook_exists:
                await conn.execute(text("ALTER TABLE profiles ADD COLUMN facebook VARCHAR"))
                print("facebook column added to profiles table.")
            else:
                print("facebook column already exists in profiles table.")
                
            if not instagram_exists:
                await conn.execute(text("ALTER TABLE profiles ADD COLUMN instagram VARCHAR"))
                print("instagram column added to profiles table.")
            else:
                print("instagram column already exists in profiles table.")
            
            # Check if gender column exists in profiles table
            result = await conn.execute(text("SELECT name FROM pragma_table_info('profiles') WHERE name = 'gender'"))
            gender_exists = result.fetchone() is not None
            
            if gender_exists:
                print("Removing gender column from profiles table...")
                
                # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
                # Get all column names except gender
                result = await conn.execute(text("PRAGMA table_info(profiles)"))
                columns = result.fetchall()
                column_names = [col[1] for col in columns if col[1] != 'gender']
                columns_str = ', '.join(column_names)
                
                # Create a new table without the gender column
                await conn.execute(text(f"CREATE TABLE profiles_new AS SELECT {columns_str} FROM profiles"))
                
                # Drop the old table
                await conn.execute(text("DROP TABLE profiles"))
                
                # Rename the new table
                await conn.execute(text("ALTER TABLE profiles_new RENAME TO profiles"))
                
                print("Gender column removed from profiles table.")
            else:
                print("Gender column does not exist in profiles table.")
                
            print("All migrations completed successfully!")
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        raise

# Run the migration when the script is executed directly
if __name__ == "__main__":
    asyncio.run(migrate())