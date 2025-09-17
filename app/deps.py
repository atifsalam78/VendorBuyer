from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
try:
    from app.config import settings
    from app.models import Base, User, ProfileImage
except ImportError:
    from config import settings
    from models import Base, User, ProfileImage

# Create async engine
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Create async session factory
async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Initialize database
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Dependency to get DB session
async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

# Dependency to get current user profile picture
async def get_current_user_profile_pic(request: Request, db: AsyncSession = Depends(get_db)):
    # Import session functions
    from app.auth import validate_session, SESSION_COOKIE_NAME
    
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    
    user_email = validate_session(session_id)
    if not user_email:
        return None
    
    # Query the database for the user
    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalars().first()
    
    if not user:
        return None
    
    # Query the profile image for the user
    profile_image_result = await db.execute(select(ProfileImage).where(ProfileImage.user_id == user.id))
    profile_image = profile_image_result.scalars().first()
    
    if profile_image and profile_image.profile_pic:
        return profile_image.profile_pic
    
    return None