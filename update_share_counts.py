import sqlite3
import sys

def update_share_counts():
    """
    Update all post shares_count values in the database to 0.
    This removes any fake share counts since there is no shares table.
    """
    try:
        # Connect to the database
        conn = sqlite3.connect('bazaarhub.db')
        cursor = conn.cursor()
        
        print("Connected to database. Updating share counts...")
        
        # Set all shares_count to 0 since there's no shares table
        cursor.execute('UPDATE posts SET shares_count = 0')
        
        # Get the number of updated rows
        updated_count = cursor.rowcount
        
        # Commit the changes
        conn.commit()
        
        # Verify the updates
        cursor.execute('SELECT id, shares_count FROM posts LIMIT 5')
        sample_posts = cursor.fetchall()
        
        print(f"\nSuccessfully reset share counts for {updated_count} posts.")
        print("\nSample of updated posts:")
        for post in sample_posts:
            print(f"Post ID: {post[0]}, Share Count: {post[1]}")
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    success = update_share_counts()
    sys.exit(0 if success else 1)