from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import secrets
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Session configuration
SESSION_COOKIE_NAME = "session_id"
SESSION_EXPIRE_HOURS = 24  # Session expires after 24 hours

# In-memory session store (for production, use Redis or database)
sessions = {}

# Password verification
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Password hashing
def get_password_hash(password):
    return pwd_context.hash(password)

# Create session
def create_session(user_email: str) -> str:
    """Create a new session for the user"""
    session_id = secrets.token_urlsafe(32)
    expiration = datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)
    
    sessions[session_id] = {
        "user_email": user_email,
        "expires_at": expiration.isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    return session_id

# Validate session
def validate_session(session_id: str) -> Optional[str]:
    """Validate session and return user email if valid"""
    if session_id not in sessions:
        return None
    
    session_data = sessions[session_id]
    expires_at = datetime.fromisoformat(session_data["expires_at"])
    
    if datetime.now() > expires_at:
        # Session expired, remove it
        del sessions[session_id]
        return None
    
    return session_data["user_email"]

# Delete session
def delete_session(session_id: str):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]

# Get current user from session
async def get_current_user(request: Request, db: AsyncSession = None) -> Optional[User]:
    """Get current user from session"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    
    user_email = validate_session(session_id)
    if not user_email:
        return None
    
    # Get user from database - import get_db locally to avoid circular imports
    if db is None:
        from app.deps import get_db
        async for db_session in get_db():
            db = db_session
            break
    
    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalars().first()
    
    return user

# Dependency to get current user email from session
async def get_current_user_email(request: Request) -> Optional[str]:
    """Get current user email from session"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    
    return validate_session(session_id)