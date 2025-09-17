import sqlite3

# Connect to the database
conn = sqlite3.connect('bazaarhub.db')
cursor = conn.cursor()

# Check if likes table exists and its structure
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables in database:', tables)

# Check likes table structure
cursor.execute('PRAGMA table_info(likes)')
likes_columns = cursor.fetchall()
print('Likes table columns:', likes_columns)

# Check posts table structure
cursor.execute('PRAGMA table_info(posts)')
posts_columns = cursor.fetchall()
print('Posts table columns:', posts_columns)

# Check if there are any likes in the database
cursor.execute('SELECT COUNT(*) FROM likes')
like_count = cursor.fetchone()[0]
print('Total likes in database:', like_count)

# Check if there are any posts
cursor.execute('SELECT COUNT(*) FROM posts')
post_count = cursor.fetchone()[0]
print('Total posts in database:', post_count)

# Check some sample posts with their like counts
cursor.execute('SELECT id, content, likes_count FROM posts LIMIT 5')
posts = cursor.fetchall()
print('Sample posts:')
for post in posts:
    print(f'  Post {post[0]}: "{post[1][:50]}..." - Likes: {post[2]}')

conn.close()