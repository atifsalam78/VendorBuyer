from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.models import User
from sqlalchemy.future import select
from email_validator import validate_email, EmailNotValidError

router = APIRouter()

@router.get("/validate/email/{email}")
async def validate_user_email(email: str, db: AsyncSession = Depends(get_db)):
    # Validate email format
    try:
        valid = validate_email(email)
        email = valid.normalized
    except EmailNotValidError:
        return {"valid": False, "message": "Invalid email format"}
    
    # Check if email exists in database
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalars().first()
    
    if existing_user:
        return {"valid": False, "message": "Email already registered"}
    
    return {"valid": True, "message": "Email is available"}

@router.get("/validate/mobile/{mobile}")
async def validate_user_mobile(mobile: str, db: AsyncSession = Depends(get_db)):
    # Basic mobile validation
    if not mobile.isdigit() or len(mobile) < 10 or len(mobile) > 12:
        return {"valid": False, "message": "Invalid mobile number format"}
    
    # Check if mobile exists in database
    result = await db.execute(select(User).where(User.mobile == mobile))
    existing_user = result.scalars().first()
    
    if existing_user:
        return {"valid": False, "message": "Mobile number already registered"}
    
    return {"valid": True, "message": "Mobile number is available"}

@router.get("/validate/ntn/{ntn}")
async def validate_ntn(ntn: str, db: AsyncSession = Depends(get_db)):
    # Basic NTN validation (example format)
    if not ntn.isdigit() or len(ntn) != 7:
        return {"valid": False, "message": "Invalid NTN format"}
    
    # In a real app, you would check if NTN exists in database
    # For now, we'll just return valid
    return {"valid": True, "message": "NTN is valid"}