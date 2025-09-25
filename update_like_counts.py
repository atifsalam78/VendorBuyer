import sqlite3
import sys

def update_like_counts():
    """
    Update all post likes_count values in the database to reflect the actual number of likes.
    This removes any fake or incorrect like counts.
    """
    try:
        # Connect to the database
        conn = sqlite3.connect('bazaarhub.db')
        cursor = conn.cursor()
        
        print("Connected to database. Updating like counts...")
        
        # Get all posts
        cursor.execute('SELECT id FROM posts')
        posts = cursor.fetchall()
        
        updated_count = 0
        for post in posts:
            post_id = post[0]
            
            # Count actual likes for this post
            cursor.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (post_id,))
            actual_count = cursor.fetchone()[0]
            
            # Update the post with the actual count
            cursor.execute('UPDATE posts SET likes_count = ? WHERE id = ?', (actual_count, post_id))
            updated_count += 1
            
            # Print progress for every 10 posts
            if updated_count % 10 == 0:
                print(f"Updated {updated_count} posts so far...")
        
        # Commit the changes
        conn.commit()
        
        # Verify the updates
        cursor.execute('SELECT id, likes_count FROM posts LIMIT 5')
        sample_posts = cursor.fetchall()
        
        print(f"\nSuccessfully updated like counts for {updated_count} posts.")
        print("\nSample of updated posts:")
        for post in sample_posts:
            print(f"Post ID: {post[0]}, Like Count: {post[1]}")
            
            # Show actual like count for verification
            cursor.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (post[0],))
            actual_count = cursor.fetchone()[0]
            print(f"  Verified count: {actual_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    success = update_like_counts()
    sys.exit(0 if success else 1)