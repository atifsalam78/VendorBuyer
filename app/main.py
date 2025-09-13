from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
import shutil
import os
from uuid import uuid4
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import routers
from app.routers import register, validate, taxonomy
from app.deps import init_db, get_db
from app.models import User, Profile, ProfileImage, Post
from app.auth import verify_password

app = FastAPI(title="BazaarHub")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(register.router, tags=["register"])
app.include_router(validate.router, tags=["validate"])
app.include_router(taxonomy.router, prefix="/taxonomy", tags=["taxonomy"])

# Create uploads directory if it doesn't exist
@app.on_event("startup")
async def create_upload_directory():
    upload_dir = Path("app/static/uploads")
    if not upload_dir.exists():
        upload_dir.mkdir(parents=True)

# Initialize database on startup
@app.on_event("startup")
async def startup_db_client():
    await init_db()

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
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
    
    # Redirect to profile page with email parameter
    return RedirectResponse(url=f"/profile?email={user_email}", status_code=303)

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: AsyncSession = Depends(get_db)):
    # Get email from session or query parameter (for testing)
    email = request.query_params.get("email")
    
    if not email:
        # Redirect to login page if no email is provided
        return RedirectResponse(url="/", status_code=303)
    
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
                "likes_count": post.likes_count,
                "comments_count": post.comments_count,
                "shares_count": post.shares_count,
                "created_at": post.created_at,
                "user_name": profile.name or user.email.split("@")[0]
            }
            for post in posts
        ]
    }
    
    return templates.TemplateResponse("profile.html", {"request": request, "user": user_data})

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
    email: str = Form(...),
    post_id: int = Form(...),
    action: str = Form(...),  # "like" or "unlike"
    db: AsyncSession = Depends(get_db)
):
    # Verify user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        return HTMLResponse("User not found", status_code=404)
    
    # Verify post exists
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalars().first()
    
    if not post:
        return HTMLResponse("Post not found", status_code=404)
    
    try:
        if action == "like":
            # Check if user already liked this post
            result = await db.execute(
                select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
            )
            existing_like = result.scalars().first()
            
            if existing_like:
                return HTMLResponse("Already liked", status_code=200)
            
            # Create new like
            new_like = Like(user_id=user.id, post_id=post_id)
            db.add(new_like)
            
            # Update post likes count
            post.likes_count += 1
            
        elif action == "unlike":
            # Find and remove the like
            result = await db.execute(
                select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
            )
            like = result.scalars().first()
            
            if like:
                await db.delete(like)
                # Update post likes count
                post.likes_count = max(0, post.likes_count - 1)
        
        await db.commit()
        
        # Return updated likes count
        return HTMLResponse(str(post.likes_count), status_code=200)
        
    except Exception as e:
        await db.rollback()
        return HTMLResponse(f"Error: {str(e)}", status_code=500)

@app.get("/feed", response_class=HTMLResponse)
async def feed(request: Request, db: AsyncSession = Depends(get_db)):
    # Fetch all public posts with user information, ordered by most recent
    result = await db.execute(
        select(Post, User.email)
        .join(User, Post.user_id == User.id)
        .where(Post.visibility == "public")
        .order_by(Post.created_at.desc())
    )
    
    posts_with_users = result.all()
    
    # Format the data for the template
    formatted_posts = []
    for post, user_email in posts_with_users:
        # Load user profile information separately
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
        
        formatted_posts.append({
            "id": post.id,
            "content": post.content,
            "image_url": post.image_url,
            "visibility": post.visibility,
            "likes_count": post.likes_count,
            "comments_count": post.comments_count,
            "shares_count": post.shares_count,
            "created_at": post.created_at,
            "user_email": user_email,
            "user_name": user_name,
            "user_profile_pic": user_profile_pic
        })
    
    return templates.TemplateResponse(
        "feed.html", 
        {
            "request": request, 
            "posts": formatted_posts,
            "current_user_email": request.cookies.get("user_email")
        }
    )

@app.get("/plans", response_class=HTMLResponse)
async def plans(request: Request):
    return templates.TemplateResponse("plans.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)