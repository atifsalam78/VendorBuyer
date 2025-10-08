from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import shutil
import os
from uuid import uuid4
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from sqlalchemy import insert, update, delete, func

# Import routers
from app.routers import register, validate, taxonomy
from app.deps import init_db, get_db, get_current_user_profile_pic
from sqlalchemy import func
from app.models import User, Profile, ProfileImage, Post, Like, Comment, Share
from app.auth import verify_password, create_session, SESSION_COOKIE_NAME, delete_session, get_current_user
from app.redis_cache import get_redis_cache, SimpleCache
from app.rate_limiter import get_rate_limiter, RateLimiter
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    # Create uploads directory if it doesn't exist
    upload_dir = Path("app/static/uploads")
    if not upload_dir.exists():
        upload_dir.mkdir(parents=True)
    
    # Initialize database
    await init_db()
    
    yield
    
    # Shutdown logic (if needed)
    pass

app = FastAPI(title="BazaarHub", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(register.router, tags=["register"])
app.include_router(validate.router, tags=["validate"])
app.include_router(taxonomy.router, prefix="/taxonomy", tags=["taxonomy"])

# Middleware to prevent caching of protected pages
@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    
    # List of protected routes that should not be cached
    protected_routes = ["/feed", "/profile", "/about", "/plans"]
    
    # Check if the current path is a protected route
    if any(request.url.path.startswith(route) for route in protected_routes):
        # Add headers to prevent caching
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    
    return response



# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user_profile_pic: str = Depends(get_current_user_profile_pic)):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user_profile_pic": current_user_profile_pic
    })

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, response: Response, email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    # Check if input is email or mobile
    is_email = '@' in email
    
    # Find user by email or mobile
    if is_email:
        result = await db.execute(select(User).where(User.email == email))
    else:
        # Try to find by mobile number
        result = await db.execute(select(User).where(User.mobile == email))
    
    user = result.scalars().first()
    
    # Check if user exists and password is correct
    if not user or not verify_password(password, user.hashed_password):
        # Return to login page with error
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid email/mobile or password"})
    
    # Get the actual email for the profile page
    user_email = user.email
    
    # Create session for the user
    session_id = create_session(user_email)
    
    # Create redirect response with secure session cookie
    response = RedirectResponse(url="/feed", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,  # Prevent JavaScript access for security
        secure=True,    # Only send over HTTPS in production
        samesite="lax", # CSRF protection
        max_age=24 * 3600  # 24 hours expiration
    )
    
    return response

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request, db: AsyncSession = Depends(get_db), current_user_profile_pic: str = Depends(get_current_user_profile_pic)):
    # Get current user from session
    current_user = await get_current_user(request, db)
    
    return templates.TemplateResponse("about.html", {
        "request": request,
        "current_user_profile_pic": current_user_profile_pic,
        "current_user_email": current_user.email if current_user else None
    })

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: AsyncSession = Depends(get_db), redis_cache: SimpleCache = Depends(get_redis_cache), current_user_profile_pic: str = Depends(get_current_user_profile_pic)):
    # Get current user from session
    current_user = await get_current_user(request, db)
    
    if not current_user:
        # Redirect to login page if no valid session
        return RedirectResponse(url="/", status_code=303)
    
    # Query the database for the user
    result = await db.execute(select(User).where(User.email == current_user.email))
    user = result.scalars().first()
    
    if not user:
        # Redirect to login page if user not found
        return RedirectResponse(url="/", status_code=303)
    
    # Query the profile for the user
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalars().first()
    
    if not profile:
        # Redirect to login page if profile not found
        return RedirectResponse(url="/", status_code=303)
    
    # Query the profile image for the user
    profile_image_result = await db.execute(select(ProfileImage).where(ProfileImage.user_id == user.id))
    profile_image = profile_image_result.scalars().first()
    
    # Query posts for the user (most recent first)
    posts_result = await db.execute(
        select(Post)
        .where(Post.user_id == user.id)
        .order_by(Post.created_at.desc())
        .limit(20)  # Limit to 20 most recent posts for performance
    )
    posts = posts_result.scalars().all()
    
    # Query shared posts by the user (internal shares only)
    shared_posts_result = await db.execute(
        select(Post, Share, User, Profile)
        .join(Share, Share.post_id == Post.id)
        .join(User, User.id == Post.user_id)
        .join(Profile, Profile.user_id == User.id)
        .where(Share.user_id == user.id, Share.share_type == "internal")
        .order_by(Share.created_at.desc())
        .limit(10)  # Limit to 10 most recent shared posts
    )
    shared_posts_data = shared_posts_result.all()
    
    # Create user data dictionary with actual user data
    user_data = {
        "id": user.id,
        "email": user.email,
        "mobile_code": user.mobile_code,
        "mobile": user.mobile,
        "gender": user.gender,
        "is_vendor": user.is_vendor,
        "profile": {
            "id": profile.id,
            "company_name": profile.company_name,
            "ntn": profile.ntn,
            "business_category": profile.business_category,
            "business_type": profile.business_type,
            "name": profile.name,
            "designation": profile.designation,
            "country": profile.country,
            "state": profile.state,
            "city": profile.city,
            "address": profile.address,
            "landline_code": profile.landline_code,
            "landline": profile.landline,
            "establishment_year": profile.establishment_year,
            "connections_count": profile.connections_count,
            "followers_count": profile.followers_count,
            "following_count": profile.following_count,
            "tagline": profile.tagline,
            "linkedin": profile.linkedin,
            "twitter": profile.twitter,
            "facebook": profile.facebook,
            "instagram": profile.instagram
        },
        "profile_image": {
            "profile_pic": profile_image.profile_pic if profile_image else None,
            "banner_pic": profile_image.banner_pic if profile_image else None
        },
        "posts": [
            {
                "id": post.id,
                "content": post.content,
                "image_url": post.image_url,
                "visibility": post.visibility,
                "likes_count": await redis_cache.get_likes_count(post.id) or post.likes_count,
                "comments_count": post.comments_count,
                "shares_count": post.shares_count,
                "created_at": post.created_at,
                "user_name": profile.name or user.email.split("@")[0]
            }
            for post in posts
        ],
        "shared_posts": [
            {
                "id": post.id,
                "content": post.content,
                "image_url": post.image_url,
                "visibility": post.visibility,
                "likes_count": await redis_cache.get_likes_count(post.id) or post.likes_count,
                "comments_count": post.comments_count,
                "shares_count": post.shares_count,
                "created_at": post.created_at,
                "shared_at": share.created_at,
                "original_author": {
                    "name": original_profile.name or original_user.email.split("@")[0],
                    "email": original_user.email
                }
            }
            for post, share, original_user, original_profile in shared_posts_data
        ]
    }
    
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": user_data,
        "current_user_profile_pic": current_user_profile_pic,
        "current_user_email": current_user.email
    })

@app.post("/upload-images", response_class=HTMLResponse)
async def upload_images(
    request: Request,
    email: str = Form(...),
    image_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Verify user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        return RedirectResponse(url="/", status_code=303)
    
    # Generate a unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid4()}.{file_extension}"
    file_path = f"app/static/uploads/{unique_filename}"
    
    # Save the uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Get or create profile image record
    result = await db.execute(select(ProfileImage).where(ProfileImage.user_id == user.id))
    profile_image = result.scalars().first()
    
    if not profile_image:
        profile_image = ProfileImage(user_id=user.id)
        db.add(profile_image)
    
    # Update the appropriate field based on image_type
    if image_type == "banner":
        profile_image.banner_pic = f"/static/uploads/{unique_filename}"
    elif image_type == "profile":
        profile_image.profile_pic = f"/static/uploads/{unique_filename}"
    
    await db.commit()
    
    return RedirectResponse(url=f"/profile?email={email}", status_code=303)

@app.post("/update-profile", response_class=HTMLResponse)
async def update_profile(request: Request, email: str = Form(...), tagline: str = Form(None), 
                        linkedin: str = Form(None), twitter: str = Form(None), 
                        facebook: str = Form(None), instagram: str = Form(None),
                        db: AsyncSession = Depends(get_db)):
    # Query the database for the user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        # Redirect to login page if user not found
        return RedirectResponse(url="/", status_code=303)
    
    # Query the profile for the user
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalars().first()
    
    if not profile:
        # Redirect to login page if profile not found
        return RedirectResponse(url="/", status_code=303)
    
    # Update profile fields
    if tagline is not None:
        profile.tagline = tagline
    
    # Always update social media fields, even if they're empty strings
    # Store the values as entered by the user - the template will handle proper URL formatting
    profile.linkedin = linkedin.strip() if linkedin is not None else ""
    profile.twitter = twitter.strip() if twitter is not None else ""
    profile.facebook = facebook.strip() if facebook is not None else ""
    profile.instagram = instagram.strip() if instagram is not None else ""
    
    # Print debug information
    print(f"Updating profile for {email}")
    print(f"LinkedIn: {profile.linkedin}")
    print(f"Twitter: {profile.twitter}")
    print(f"Facebook: {profile.facebook}")
    print(f"Instagram: {profile.instagram}")
    
    # Commit changes to database
    await db.commit()
    
    # Redirect back to profile page
    return RedirectResponse(url=f"/profile?email={email}", status_code=303)

# Helper function to update post comments count
async def update_post_comments_count(db: AsyncSession, post_id: int) -> int:
    """Update the comments_count for a post based on actual comment count in the database"""
    # Count actual comments for the post
    result = await db.execute(
        select(func.count(Comment.id)).where(Comment.post_id == post_id)
    )
    actual_count = result.scalar()
    
    # Update the post with the actual count
    await db.execute(
        update(Post)
        .where(Post.id == post_id)
        .values(comments_count=actual_count)
    )
    
    return actual_count

# Comment endpoints
@app.post("/create-comment", response_class=HTMLResponse)
async def create_comment(
    request: Request,
    email: str = Form(...),
    post_id: int = Form(...),
    content: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # Verify user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        return RedirectResponse(url="/", status_code=303)
    
    # Verify post exists
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalars().first()
    
    if not post:
        return RedirectResponse(url="/feed", status_code=303)
    
    # Create new comment
    new_comment = Comment(
        user_id=user.id,
        post_id=post_id,
        content=content
    )
    
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)
    
    # Update post comments count with actual count
    await update_post_comments_count(db, post_id)
    
    # Redirect back to the page where the comment was made
    referer = request.headers.get("referer", "/feed")
    return RedirectResponse(url=referer, status_code=303)

@app.get("/admin/update-all-comment-counts", response_class=HTMLResponse)
async def update_all_comment_counts(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Get all posts
    result = await db.execute(select(Post))
    posts = result.scalars().all()
    
    updated_count = 0
    for post in posts:
        # Update each post's comment count
        actual_count = await update_post_comments_count(db, post.id)
        updated_count += 1
    
    await db.commit()
    
    return HTMLResponse(f"Updated comment counts for {updated_count} posts.")

@app.get("/test-comments/{post_id}", response_class=HTMLResponse)
async def test_comments(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Simple test endpoint to check if comments functionality works"""
    try:
        print(f"Testing comments for post {post_id}")
        
        # Simple test - just return a basic response
        return HTMLResponse(f"Test successful for post {post_id}")
    except Exception as e:
        print(f"Error in test_comments: {str(e)}")
        return HTMLResponse(f"Test error: {str(e)}", status_code=500)

@app.get("/comments/{post_id}", response_class=HTMLResponse)
async def get_comments(
    request: Request,
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        # First, let's test if we can connect to the database
        print(f"Getting comments for post {post_id}")
        
        # Get comments for the post with user information
        result = await db.execute(
            select(Comment, User.email)
            .join(User, Comment.user_id == User.id)
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at.asc())
        )
        
        comments_with_users = result.all()
        print(f"Found {len(comments_with_users)} comments")
        
        # Format comments for response
        formatted_comments = []
        for comment, user_email in comments_with_users:
            formatted_comments.append({
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at,
                "user_email": user_email,
                "user_name": user_email.split('@')[0] if user_email else "[user deleted]"
            })
        
        # Test with simple response first
        if not formatted_comments:
            return HTMLResponse("No comments found for this post")
        
        return templates.TemplateResponse(
            "comments_partial.html", 
            {
                "request": request, 
                "comments": formatted_comments,
                "post_id": post_id
            }
        )
    except Exception as e:
        # Return a simple error message for debugging
        print(f"Error in get_comments: {str(e)}")
        return HTMLResponse(f"Error loading comments: {str(e)}", status_code=500)

@app.post("/create-post", response_class=HTMLResponse)
async def create_post(
    request: Request,
    email: str = Form(...),
    content: str = Form(...),
    visibility: str = Form("public"),
    post_image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    # Verify user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        return RedirectResponse(url="/", status_code=303)
    
    # Handle image upload if provided
    image_url = None
    if post_image and post_image.filename:
        # Generate a unique filename
        file_extension = post_image.filename.split(".")[-1]
        unique_filename = f"{uuid4()}.{file_extension}"
        file_path = f"app/static/uploads/{unique_filename}"
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(post_image.file, buffer)
        
        image_url = f"/static/uploads/{unique_filename}"
    
    # Create new post
    new_post = Post(
        user_id=user.id,
        content=content,
        image_url=image_url,
        visibility=visibility
    )
    
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)
    
    # Redirect back to profile page
    return RedirectResponse(url=f"/profile?email={email}", status_code=303)

@app.post("/like-post", response_class=HTMLResponse)
async def like_post(
    request: Request,
    email: str = Form(None),  # Optional - for backward compatibility
    session_id: str = Form(None),  # New parameter for session-based authentication
    post_id: int = Form(...),
    action: str = Form(...),  # "like" or "unlike"
    db: AsyncSession = Depends(get_db),
    redis_cache: SimpleCache = Depends(get_redis_cache),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    try:
        # Debug logging
        print(f"Like request - email: {email}, session_id: {session_id}, post_id: {post_id}, action: {action}")
        
        # Determine user email from session or direct email parameter
        user_email = None
        if session_id:
            # Validate session and get user email
            user_email = validate_session(session_id)
            if not user_email:
                return HTMLResponse("Invalid session", status_code=401)
        elif email:
            # Use direct email parameter (for backward compatibility)
            user_email = email
        else:
            return HTMLResponse("Authentication required", status_code=401)
        
        # Get user and post in a single query using joins to reduce round trips
        result = await db.execute(
            select(User, Post)
            .join(Post, Post.id == post_id)
            .where(User.email == user_email)
        )
        user_post = result.first()
        
        if not user_post:
            return HTMLResponse("User or post not found", status_code=404)
        
        user, post = user_post
        
        # Apply rate limiting for like actions only
        if action == "like":
            # Check rate limit
            if not await rate_limiter.check_rate_limit(user.id, "like"):
                return HTMLResponse("Rate limit exceeded. Please try again later.", status_code=429)
            
            # Increment rate limit counter
            await rate_limiter.increment_rate_limit(user.id, "like")
            
            # Check if like already exists and handle like/unlike in single transaction
            existing_like_result = await db.execute(
                select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
            )
            existing_like = existing_like_result.scalars().first()
            
            if existing_like:
                # User already liked this post
                return HTMLResponse("Already liked", status_code=200)
            
            # Insert new like and update count in single operation
            new_like = Like(user_id=user.id, post_id=post_id)
            db.add(new_like)
            
            # Update likes count directly
            post.likes_count += 1
                
        elif action == "unlike":
            # Delete like and update count in single operation
            delete_result = await db.execute(
                delete(Like)
                .where(Like.user_id == user.id, Like.post_id == post_id)
            )
            
            if delete_result.rowcount > 0:
                # Only update count if a like was actually removed
                post.likes_count -= 1
        
        await db.commit()
        
        # Force refresh the post object to get the latest count from database
        await db.refresh(post)
        
        # Update Redis cache with the actual database value
        await redis_cache.set_likes_count(post_id, post.likes_count)
        
        print(f"Returning likes count: {post.likes_count}")
        return HTMLResponse(str(post.likes_count), status_code=200)
        
    except Exception as e:
        await db.rollback()
        return HTMLResponse(f"Error: {str(e)}", status_code=500)

@app.get("/api/user/{user_id}/shared-posts")
async def get_user_shared_posts(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Get shared posts for a specific user"""
    try:
        # Get user's shared posts with post details
        shared_posts_result = await db.execute(
            select(Share).where(Share.user_id == user_id).order_by(Share.created_at.desc()).limit(20)
        )
        shared_posts = shared_posts_result.scalars().all()
        
        shared_posts_data = []
        for share in shared_posts:
            post_result = await db.execute(select(Post).where(Post.id == share.post_id))
            post = post_result.scalars().first()
            if post:
                # Get post author info
                author_result = await db.execute(select(User).where(User.id == post.user_id))
                author = author_result.scalars().first()
                
                post_data = {
                    "id": post.id,
                    "content": post.content,
                    "image_url": post.image_url,
                    "created_at": post.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "likes_count": post.likes_count,
                    "shares_count": post.shares_count,
                    "author": {
                        "id": author.id,
                        "email": author.email
                    },
                    "shared_at": share.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
                shared_posts_data.append(post_data)
        
        return {"shared_posts": shared_posts_data}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/share-post", response_class=HTMLResponse)
async def share_post(
    request: Request,
    email: str = Form(None),  # Optional - for backward compatibility
    session_id: str = Form(None),  # New parameter for session-based authentication
    post_id: int = Form(...),
    share_type: str = Form("internal"),  # "internal", "external_link", "facebook", "twitter", etc.
    db: AsyncSession = Depends(get_db),
    redis_cache: SimpleCache = Depends(get_redis_cache)
):
    try:
        # Debug logging
        print(f"Share request - email: {email}, session_id: {session_id}, post_id: {post_id}, share_type: {share_type}")
        
        # Determine user email from session or direct email parameter
        user_email = None
        if session_id:
            # Validate session and get user email
            user_email = validate_session(session_id)
            if not user_email:
                return HTMLResponse("Invalid session", status_code=401)
        elif email:
            # Use direct email parameter (for backward compatibility)
            user_email = email
        else:
            return HTMLResponse("Authentication required", status_code=401)
        
        # Get user and post in a single query using joins to reduce round trips
        result = await db.execute(
            select(User, Post)
            .join(Post, Post.id == post_id)
            .where(User.email == user_email)
        )
        user_post = result.first()
        
        if not user_post:
            return HTMLResponse("User or post not found", status_code=404)
        
        user, post = user_post
        
        # Check if share already exists for internal shares (prevent duplicate internal shares)
        if share_type == "internal":
            existing_share_result = await db.execute(
                select(Share).where(Share.user_id == user.id, Share.post_id == post_id, Share.share_type == "internal")
            )
            existing_share = existing_share_result.scalars().first()
            
            if existing_share:
                # User already shared this post internally
                return HTMLResponse("Already shared", status_code=200)
        
        # Insert new share and update count in single operation
        new_share = Share(user_id=user.id, post_id=post_id, share_type=share_type)
        db.add(new_share)
        
        # Update shares count directly
        post.shares_count += 1
        
        await db.commit()
        
        # Force refresh the post object to get the latest count from database
        await db.refresh(post)
        
        # Update Redis cache with the actual database value
        await redis_cache.set_shares_count(post_id, post.shares_count)
        
        print(f"Returning shares count: {post.shares_count}")
        return HTMLResponse(str(post.shares_count), status_code=200)
        
    except Exception as e:
        await db.rollback()
        return HTMLResponse(f"Error: {str(e)}", status_code=500)

@app.get("/feed", response_class=HTMLResponse)
async def feed(request: Request, page: int = 1, db: AsyncSession = Depends(get_db), redis_cache: SimpleCache = Depends(get_redis_cache), current_user_profile_pic: str = Depends(get_current_user_profile_pic)):
    # Get current user from session
    current_user = await get_current_user(request, db)
    
    if not current_user:
        # Redirect to login page if no valid session
        return RedirectResponse(url="/", status_code=303)

    # Fetch current user's profile and banner for sidebar card
    current_user_name = current_user.email.split('@')[0]
    current_user_tagline = None
    current_user_company_name = None
    current_user_banner_pic = None

    try:
        profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
        profile = profile_result.scalars().first()
        if profile:
            if profile.name:
                current_user_name = profile.name
            current_user_tagline = profile.tagline
            current_user_company_name = profile.company_name

        profile_image_result = await db.execute(select(ProfileImage).where(ProfileImage.user_id == current_user.id))
        profile_image = profile_image_result.scalars().first()
        if profile_image:
            current_user_banner_pic = profile_image.banner_pic
    except Exception:
        # Fail silently; sidebar will render with available defaults
        pass

    # Pagination settings
    posts_per_page = 10
    offset = (page - 1) * posts_per_page
    
    # Fetch total count of public posts and shared posts
    total_posts_result = await db.execute(
        select(func.count()).select_from(Post)
        .where(Post.visibility == "public")
    )
    total_posts = total_posts_result.scalar()
    
    total_shares_result = await db.execute(
        select(func.count()).select_from(Share)
        .join(Post, Share.post_id == Post.id)
        .where(Post.visibility == "public")
    )
    total_shares = total_shares_result.scalar()
    
    total_items = total_posts + total_shares
    
    # Calculate total pages
    total_pages = (total_items + posts_per_page - 1) // posts_per_page
    
    # Fetch paginated public posts with user information
    posts_result = await db.execute(
        select(Post, User.email)
        .outerjoin(User, Post.user_id == User.id)
        .where(Post.visibility == "public")
        .order_by(Post.created_at.desc())
    )
    posts_with_users = posts_result.all()
    
    # Fetch shared posts with sharer and original author information
    shares_result = await db.execute(
        select(Share, Post, User.email.label('sharer_email'), User.id.label('sharer_id'))
        .join(Post, Share.post_id == Post.id)
        .join(User, Share.user_id == User.id)
        .where(Post.visibility == "public")
        .order_by(Share.created_at.desc())
    )
    shares_with_info = shares_result.all()
    
    # Combine and sort all items by timestamp
    all_items = []
    
    # Add original posts
    for post, user_email in posts_with_users:
        all_items.append({
            'type': 'post',
            'timestamp': post.created_at,
            'data': (post, user_email)
        })
    
    # Add shared posts
    for share, post, sharer_email, sharer_id in shares_with_info:
        all_items.append({
            'type': 'share',
            'timestamp': share.created_at,
            'data': (share, post, sharer_email, sharer_id)
        })
    
    # Sort by timestamp (most recent first)
    all_items.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Apply pagination
    paginated_items = all_items[offset:offset + posts_per_page]
    
    # Format the data for the template
    formatted_posts = []
    for item in paginated_items:
        if item['type'] == 'post':
            post, user_email = item['data']
            
            # Handle case where user doesn't exist
            if user_email is None:
                user_name = "[user deleted]"
                user_profile_pic = None
            else:
                user_name = user_email.split('@')[0]
                user_profile_pic = None
            
            # Query for the user's profile
            profile_result = await db.execute(
                select(Profile).where(Profile.user_id == post.user_id)
            )
            profile = profile_result.scalars().first()
            
            if profile:
                user_name = profile.name if profile.name else user_name
                # Query for profile image if profile exists
                profile_image_result = await db.execute(
                    select(ProfileImage).where(ProfileImage.user_id == post.user_id)
                )
                profile_image = profile_image_result.scalars().first()
                if profile_image:
                    user_profile_pic = profile_image.profile_pic
            
            # Get likes count from Redis cache first, fallback to database
            cached_likes = await redis_cache.get_likes_count(post.id)
            likes_count = cached_likes if cached_likes is not None else post.likes_count
            
            formatted_posts.append({
                "id": post.id,
                "content": post.content,
                "image_url": post.image_url,
                "visibility": post.visibility,
                "likes_count": likes_count,
                "comments_count": post.comments_count,
                "shares_count": post.shares_count,
                "created_at": post.created_at,
                "user_email": user_email,
                "user_name": user_name,
                "user_profile_pic": user_profile_pic,
                "is_shared": False
            })
            
        elif item['type'] == 'share':
            share, post, sharer_email, sharer_id = item['data']
            
            # Get original post author info
            original_author_result = await db.execute(
                select(User).where(User.id == post.user_id)
            )
            original_author = original_author_result.scalars().first()
            
            original_author_name = "[user deleted]"
            original_author_profile_pic = None
            
            if original_author:
                original_author_name = original_author.email.split('@')[0]
                
                # Get original author's profile
                original_profile_result = await db.execute(
                    select(Profile).where(Profile.user_id == original_author.id)
                )
                original_profile = original_profile_result.scalars().first()
                
                if original_profile and original_profile.name:
                    original_author_name = original_profile.name
                    
                    # Get original author's profile image
                    original_profile_image_result = await db.execute(
                        select(ProfileImage).where(ProfileImage.user_id == original_author.id)
                    )
                    original_profile_image = original_profile_image_result.scalars().first()
                    if original_profile_image:
                        original_author_profile_pic = original_profile_image.profile_pic
            
            # Get sharer info
            sharer_name = sharer_email.split('@')[0] if sharer_email else "[user deleted]"
            sharer_profile_pic = None
            
            sharer_profile_result = await db.execute(
                select(Profile).where(Profile.user_id == sharer_id)
            )
            sharer_profile = sharer_profile_result.scalars().first()
            
            if sharer_profile and sharer_profile.name:
                sharer_name = sharer_profile.name
                
                # Get sharer's profile image
                sharer_profile_image_result = await db.execute(
                    select(ProfileImage).where(ProfileImage.user_id == sharer_id)
                )
                sharer_profile_image = sharer_profile_image_result.scalars().first()
                if sharer_profile_image:
                    sharer_profile_pic = sharer_profile_image.profile_pic
            
            # Get likes count from Redis cache first, fallback to database
            cached_likes = await redis_cache.get_likes_count(post.id)
            likes_count = cached_likes if cached_likes is not None else post.likes_count
            
            formatted_posts.append({
                "id": post.id,
                "content": post.content,
                "image_url": post.image_url,
                "visibility": post.visibility,
                "likes_count": likes_count,
                "comments_count": post.comments_count,
                "shares_count": post.shares_count,
                "created_at": post.created_at,
                "user_email": original_author.email if original_author else None,
                "user_name": original_author_name,
                "user_profile_pic": original_author_profile_pic,
                "is_shared": True,
                "shared_at": share.created_at,
                "sharer_name": sharer_name,
                "sharer_email": sharer_email,
                "sharer_profile_pic": sharer_profile_pic
            })

    return templates.TemplateResponse(
        "feed.html", 
        {
            "request": request, 
            "posts": formatted_posts,
            "current_user_email": current_user.email,
            "current_user_profile_pic": current_user_profile_pic,
            "current_user_name": current_user_name,
            "current_user_tagline": current_user_tagline,
            "current_user_company_name": current_user_company_name,
            "current_user_banner_pic": current_user_banner_pic,
            "current_page": page,
            "total_pages": total_pages,
            "total_posts": total_items,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1,
            "prev_page": page - 1
        }
    )

@app.get("/api/posts/{post_id}/likes", response_class=JSONResponse)
async def get_post_likes(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Get users who liked the post
    result = await db.execute(
        select(User.email, Profile.name, ProfileImage.profile_pic)
        .join(Like, Like.user_id == User.id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .outerjoin(ProfileImage, ProfileImage.user_id == User.id)
        .where(Like.post_id == post_id)
        .order_by(Like.created_at.desc())
        .limit(50)  # Limit to 50 users for performance
    )
    
    likes = result.all()
    
    # Format the response
    users = []
    for email, name, profile_pic in likes:
        display_name = name if name else email.split('@')[0]
        users.append({
            "email": email,
            "name": display_name,
            "profile_pic": profile_pic
        })
    
    return {"users": users}

@app.get("/api/posts/{post_id}/shares", response_class=JSONResponse)
async def get_post_shares(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Get users who shared the post
    result = await db.execute(
        select(User.email, Profile.name, ProfileImage.profile_pic, Share.share_type, Share.created_at)
        .join(Share, Share.user_id == User.id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .outerjoin(ProfileImage, ProfileImage.user_id == User.id)
        .where(Share.post_id == post_id)
        .order_by(Share.created_at.desc())
        .limit(50)  # Limit to 50 shares for performance
    )
    
    shares = result.all()
    
    # Format the response
    users = []
    for share in shares:
        users.append({
            "email": share.email,
            "name": share.name or share.email.split('@')[0],
            "profile_pic": share.profile_pic or "/static/uploads/default-avatar.png",
            "share_type": share.share_type,
            "shared_at": share.created_at.isoformat() if share.created_at else None
        })
    
    return {"users": users}

@app.get("/api/posts/{post_id}/comments", response_class=JSONResponse)
async def get_post_comments(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Get users who commented on the post with their comments
    result = await db.execute(
        select(User.email, Profile.name, ProfileImage.profile_pic, Comment.content)
        .join(Comment, Comment.user_id == User.id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .outerjoin(ProfileImage, ProfileImage.user_id == User.id)
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.desc())
        .limit(50)  # Limit to 50 comments for performance
    )
    
    comments = result.all()
    
    # Format the response
    users = []
    for email, name, profile_pic, content in comments:
        display_name = name if name else email.split('@')[0]
        users.append({
            "email": email,
            "name": display_name,
            "profile_pic": profile_pic,
            "comment_text": content
        })
    
    return {"users": users}

@app.get("/plans", response_class=HTMLResponse)
async def plans(request: Request, db: AsyncSession = Depends(get_db), current_user_profile_pic: str = Depends(get_current_user_profile_pic)):
    # Get current user from session
    current_user = await get_current_user(request, db)
    
    return templates.TemplateResponse("plans.html", {
        "request": request,
        "current_user_profile_pic": current_user_profile_pic,
        "current_user_email": current_user.email if current_user else None
    })

@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request, response: Response):
    # Get session ID from cookie
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    
    # Delete the session if it exists
    if session_id:
        delete_session(session_id)
    
    # Create redirect response that clears the session cookie
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    
    return response

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)