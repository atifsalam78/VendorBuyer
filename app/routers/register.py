from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.models import User, Profile
from app.schemas import UserCreate, ProfileCreate
from app.auth import get_password_hash
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/register")
async def register_user(
    request: Request,
    email: str = Form(...),
    mobile: str = Form(...),
    password: str = Form(...),
    is_vendor: bool = Form(False),
    company_name: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(password)
    new_user = User(
        email=email,
        mobile=mobile,
        hashed_password=hashed_password,
        is_vendor=is_vendor
    )
    
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Registration failed")
    
    # Create profile
    new_profile = Profile(
        user_id=new_user.id,
        company_name=company_name
    )
    
    db.add(new_profile)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Profile creation failed")
    
    # Redirect to profile page
    return RedirectResponse(url="/profile", status_code=303)